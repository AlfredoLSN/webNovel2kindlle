from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from webnovel2kindle.models import Chapter, ChapterContent, Novel, NovelMetadata, Volume

CHAPTER_RE = re.compile(r"\b(?:chapter|capitulo|capítulo|cap\.?|ch\.?)\s*(\d+)\b", re.IGNORECASE)
VOL_CAP_RE = re.compile(
    r"\bvol\.?\s*(?P<volume>.+?)\s+cap\.?\s*(?P<chapter>\d+)\b",
    re.IGNORECASE,
)
VOLUME_RE = re.compile(r"\b(?:volume|vol\.?|book|arc|season)\b", re.IGNORECASE)
VOLUME_NUMBER_TITLE_RE = re.compile(r"^volume\s+(\d+)$", re.IGNORECASE)


def parse_novel_page(html: str, page_url: str) -> Novel:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    metadata = _extract_metadata(soup, page_url)
    centralnovel_volumes = _extract_eplister_volumes(soup, page_url)
    if centralnovel_volumes:
        return Novel(
            title=title,
            url=page_url,
            volumes=tuple(centralnovel_volumes),
            metadata=metadata,
        )

    chapters = _extract_chapter_links(soup, page_url)
    volumes = _group_chapters_by_volume(soup, chapters)

    return Novel(title=title, url=page_url, volumes=tuple(volumes), metadata=metadata)


def parse_chapter_page(html: str) -> ChapterContent:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_chapter_title(soup)
    content = soup.select_one(".epcontent") or soup.select_one(".entry-content")
    if not content:
        return ChapterContent(title=title, html="<p>Conteudo nao encontrado.</p>")

    for unwanted in content.select("script, style, iframe, ins, .code-block, .sharedaddy"):
        unwanted.decompose()

    paragraphs = []
    for child in content.find_all(["p", "h2", "h3", "blockquote"], recursive=False):
        text = _clean_text(child.get_text(" ", strip=True))
        if text:
            tag = child.name if child.name in {"h2", "h3", "blockquote"} else "p"
            paragraphs.append(f"<{tag}>{_escape_xml(text)}</{tag}>")

    if not paragraphs:
        text = content.get_text("\n", strip=True)
        paragraphs = [
            f"<p>{_escape_xml(line)}</p>"
            for line in text.splitlines()
            if _clean_text(line)
        ]

    return ChapterContent(title=title, html="\n".join(paragraphs))


def _extract_chapter_title(soup: BeautifulSoup) -> str:
    page_title = _extract_title(soup)
    chapter_name_node = soup.select_one(".cat-series")
    if not chapter_name_node:
        return page_title

    chapter_name = _clean_text(chapter_name_node.get_text(" ", strip=True))
    if not chapter_name or chapter_name.casefold() in page_title.casefold():
        return page_title

    chapter_number = _chapter_number(page_title)
    if chapter_number is not None:
        return f"Capítulo {chapter_number} - {chapter_name}"

    return f"{page_title} - {chapter_name}"


def _extract_eplister_volumes(soup: BeautifulSoup, page_url: str) -> list[Volume]:
    volumes: dict[str, list[Chapter]] = {}
    seen_urls: set[str] = set()

    for chapter_list in soup.select(".eplister"):
        for anchor in chapter_list.find_all("a", href=True):
            href = anchor["href"]
            if href.rstrip("/").endswith("/pdf"):
                continue

            title = _clean_text(anchor.get_text(" ", strip=True))
            if not title or "{{" in title:
                continue

            url = urljoin(page_url, href)
            if url in seen_urls:
                continue

            volume_title = _volume_title(title)
            volumes.setdefault(volume_title, []).append(
                Chapter(title=title, url=url, number=_chapter_number(title, url))
            )
            seen_urls.add(url)

    parsed = [
        Volume(title=volume_title, chapters=tuple(_sort_chapters(chapters)))
        for volume_title, chapters in volumes.items()
    ]
    return sorted(parsed, key=_volume_sort_key)


def _extract_metadata(soup: BeautifulSoup, page_url: str) -> NovelMetadata:
    fields = _extract_info_fields(soup)
    return NovelMetadata(
        author=fields.get("Autor"),
        status=fields.get("Status"),
        novel_type=fields.get("Tipo"),
        release_year=fields.get("Lançamento") or fields.get("Lancamento"),
        posted_at=fields.get("Postado em"),
        updated_at=fields.get("Atualizado em"),
        description=_extract_description(soup),
        cover_url=_extract_cover_url(soup, page_url),
        genres=tuple(_extract_genres(soup)),
    )


def _extract_info_fields(soup: BeautifulSoup) -> dict[str, str]:
    fields: dict[str, str] = {}
    for node in soup.select(".spe span"):
        text = _clean_text(node.get_text(" ", strip=True))
        if ":" not in text:
            continue
        key, value = text.split(":", 1)
        fields[_clean_text(key)] = _clean_text(value.strip(" ,"))
    return fields


def _extract_description(soup: BeautifulSoup) -> str | None:
    content = soup.select_one(".entry-content")
    if not content:
        return None

    paragraphs: list[str] = []
    for node in content.find_all(["p", "div", "hr"], recursive=False):
        if node.name == "hr":
            break

        text = _clean_text(node.get_text(" ", strip=True))
        if not text:
            continue
        if _is_description_stop_text(text):
            break

        if text.lower().startswith("sinopse:"):
            text = _clean_text(text.split(":", 1)[1])
            if not text:
                continue

        paragraphs.append(text)

    return "\n\n".join(paragraphs) or None


def _is_description_stop_text(text: str) -> bool:
    normalized = text.casefold()
    stop_prefixes = (
        "aviso",
        "este conteúdo foi traduzido",
        "este conteudo foi traduzido",
        "se você possui os direitos legais",
        "se voce possui os direitos legais",
        "para outros assuntos",
        "confira outras músicas",
        "confira outras musicas",
        "se curtiu",
        "download",
    )
    return any(normalized.startswith(prefix) for prefix in stop_prefixes)


def _extract_cover_url(soup: BeautifulSoup, page_url: str) -> str | None:
    selectors = [
        "img.ts-post-image",
        "img.wp-post-image",
        'meta[property="og:image"]',
        ".bigcover img",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        value = (
            node.get("content")
            if node.name == "meta"
            else node.get("src") or node.get("data-src")
        )
        if value:
            return urljoin(page_url, value)
    return None


def _extract_genres(soup: BeautifulSoup) -> list[str]:
    genres: list[str] = []
    for node in soup.select(".genxed, .mgen a, .seriestugenre a"):
        text = _clean_text(node.get_text(" ", strip=True))
        if text and text not in genres:
            genres.append(text)
    return genres


def _extract_title(soup: BeautifulSoup) -> str:
    selectors = [
        "h1.entry-title",
        "h1.novel-title",
        ".post-title h1",
        ".summary-heading h1",
        ".series-title",
        "h1",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                return text

    if soup.title and soup.title.string:
        return _clean_text(soup.title.string)

    return "Obra sem titulo"


def _extract_chapter_links(soup: BeautifulSoup, page_url: str) -> list[Chapter]:
    anchors = [
        anchor
        for anchor in soup.find_all("a", href=True)
        if _looks_like_chapter_anchor(anchor, anchor["href"])
    ]

    chapters: list[Chapter] = []
    seen_urls: set[str] = set()
    for anchor in anchors:
        url = urljoin(page_url, anchor["href"])
        if url in seen_urls:
            continue

        title = _clean_text(anchor.get_text(" ", strip=True))
        if not title:
            continue

        chapters.append(Chapter(title=title, url=url, number=_chapter_number(title, url)))
        seen_urls.add(url)

    return _sort_chapters(chapters)


def _looks_like_chapter_anchor(anchor: Tag, href: str) -> bool:
    text = _clean_text(anchor.get_text(" ", strip=True))
    if not text:
        return False

    haystack = f"{text} {href}".lower()
    class_haystack = " ".join(anchor.get("class", [])).lower()
    parent_class_names = anchor.parent.get("class", []) if isinstance(anchor.parent, Tag) else []
    parent_classes = " ".join(parent_class_names)

    return any(
        [
            "chapter" in haystack,
            "capitulo" in haystack,
            "capítulo" in haystack,
            "chapter" in class_haystack,
            "wp-manga-chapter" in parent_classes,
            bool(CHAPTER_RE.search(text)),
        ]
    )


def _sort_chapters(chapters: list[Chapter]) -> list[Chapter]:
    if len(chapters) < 2:
        return chapters

    numbered = [chapter for chapter in chapters if chapter.number is not None]
    if len(numbered) >= max(2, len(chapters) // 2):
        return sorted(chapters, key=lambda chapter: chapter.number or 0)

    return chapters


def _group_chapters_by_volume(soup: BeautifulSoup, chapters: list[Chapter]) -> list[Volume]:
    if not chapters:
        return []

    by_url = {chapter.url: chapter for chapter in chapters}
    volumes = _volumes_from_headings(soup, by_url)
    if volumes:
        assigned = {chapter.url for volume in volumes for chapter in volume.chapters}
        remaining = [chapter for chapter in chapters if chapter.url not in assigned]
        if remaining:
            volumes.append(Volume(title="Sem volume", chapters=tuple(remaining)))
        return volumes

    return [Volume(title="Capitulos", chapters=tuple(chapters))]


def _volumes_from_headings(soup: BeautifulSoup, by_url: dict[str, Chapter]) -> list[Volume]:
    content = _main_content(soup)
    volume_nodes = [
        node
        for node in content.find_all(["h2", "h3", "h4", "strong", "p", "div"])
        if _looks_like_volume_heading(node)
    ]

    volumes: list[Volume] = []
    used_urls: set[str] = set()

    for node in volume_nodes:
        chapter_urls = _chapter_urls_until_next_volume(node, by_url)
        chapter_list = [by_url[url] for url in chapter_urls if url not in used_urls]
        if chapter_list:
            used_urls.update(chapter.url for chapter in chapter_list)
            volumes.append(
                Volume(
                    title=_clean_text(node.get_text(" ", strip=True)),
                    chapters=tuple(chapter_list),
                )
            )

    return volumes


def _chapter_urls_until_next_volume(node: Tag, by_url: dict[str, Chapter]) -> list[str]:
    urls: list[str] = []
    for sibling in node.next_elements:
        if sibling is node:
            continue
        if isinstance(sibling, Tag) and sibling is not node and _looks_like_volume_heading(sibling):
            break
        if isinstance(sibling, Tag) and sibling.name == "a" and sibling.has_attr("href"):
            normalized = _normalize_known_url(sibling["href"], by_url)
            if normalized:
                urls.append(normalized)
    return urls


def _normalize_known_url(href: str, by_url: dict[str, Chapter]) -> str | None:
    href_path = urlparse(href).path.rstrip("/")
    for url in by_url:
        if urlparse(url).path.rstrip("/") == href_path:
            return url
    return None


def _looks_like_volume_heading(node: Tag) -> bool:
    text = _clean_text(node.get_text(" ", strip=True))
    if not text or len(text) > 120:
        return False
    return bool(VOLUME_RE.search(text))


def _main_content(soup: BeautifulSoup) -> Tag | BeautifulSoup:
    for selector in ["main", "article", ".entry-content", ".post-content", ".page-content"]:
        node = soup.select_one(selector)
        if node:
            return node
    return soup


def _chapter_number(*values: str) -> int | None:
    for value in values:
        vol_cap_match = VOL_CAP_RE.search(value)
        if vol_cap_match:
            return int(vol_cap_match.group("chapter"))

        match = CHAPTER_RE.search(value)
        if match:
            return int(match.group(1))
    return None


def _volume_title(value: str) -> str:
    match = VOL_CAP_RE.search(value)
    if not match:
        return "Capitulos"

    volume = _clean_text(match.group("volume"))
    if volume.casefold() == "extra":
        return "Volume Extra"
    if volume.isdigit():
        return f"Volume {int(volume)}"
    return f"Volume {volume}"


def _volume_sort_key(volume: Volume) -> tuple[int, int]:
    match = VOLUME_NUMBER_TITLE_RE.search(volume.title)
    if match:
        return (1, int(match.group(1)))
    if "extra" in volume.title.lower():
        return (0, 0)
    chapter_numbers = [
        chapter.number
        for chapter in volume.chapters
        if chapter.number is not None
    ]
    if chapter_numbers:
        return (2, min(chapter_numbers))
    return (3, 0)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
