from __future__ import annotations

import mimetypes
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from webnovel2kindle.models import ChapterContent, Novel, Volume

GENERATOR_NAME = "webnovel2kindle"


@dataclass(frozen=True)
class CoverImage:
    data: bytes
    media_type: str
    extension: str


def build_epub(
    novel: Novel,
    volume: Volume,
    chapters: list[ChapterContent],
    output_path: Path,
    cover: CoverImage | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, novel.url + '#' + volume.title)}"
    modified = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    chapter_files = [f"chapters/chapter-{index:04d}.xhtml" for index in range(1, len(chapters) + 1)]
    cover_href = f"images/cover{cover.extension}" if cover else None

    with zipfile.ZipFile(output_path, "w") as epub:
        epub.writestr(
            zipfile.ZipInfo("mimetype", date_time=(1980, 1, 1, 0, 0, 0)),
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        _write(epub, "META-INF/container.xml", _container_xml())
        _write(epub, "OEBPS/styles/book.css", _book_css())
        _write(epub, "OEBPS/title.xhtml", _title_page(novel, volume, cover_href))
        _write(epub, "OEBPS/metadata.xhtml", _metadata_page(novel))
        _write(epub, "OEBPS/signature.xhtml", _signature_page(novel))
        _write(epub, "OEBPS/nav.xhtml", _nav_page(novel, volume, chapters, chapter_files))
        _write(epub, "OEBPS/toc.ncx", _toc_ncx(book_id, novel, volume, chapters, chapter_files))
        _write(
            epub,
            "OEBPS/content.opf",
            _content_opf(book_id, modified, novel, volume, chapters, chapter_files, cover),
        )

        if cover and cover_href:
            epub.writestr(f"OEBPS/{cover_href}", cover.data, compress_type=zipfile.ZIP_DEFLATED)

        for chapter, file_name in zip(chapters, chapter_files, strict=True):
            _write(epub, f"OEBPS/{file_name}", _chapter_page(chapter))

    return output_path


def cover_from_response(data: bytes, content_type: str | None, source_url: str) -> CoverImage:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        media_type = mimetypes.guess_type(source_url)[0] or "image/jpeg"

    extension = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(media_type, ".jpg")

    return CoverImage(data=data, media_type=media_type, extension=extension)


def epub_file_name(novel: Novel, volume: Volume) -> str:
    return f"{_slugify(novel.title)}-{_slugify(volume.title)}.epub"


def _write(epub: zipfile.ZipFile, path: str, content: str) -> None:
    epub.writestr(path, content.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)


def _container_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _content_opf(
    book_id: str,
    modified: str,
    novel: Novel,
    volume: Volume,
    chapters: list[ChapterContent],
    chapter_files: list[str],
    cover: CoverImage | None,
) -> str:
    metadata = novel.metadata
    subject_tags = "\n".join(
        f"    <dc:subject>{escape(genre)}</dc:subject>" for genre in metadata.genres
    )
    creator = escape(metadata.author or "Autor desconhecido")
    description = escape(metadata.description or f"{novel.title} - {volume.title}")
    cover_item = ""
    cover_meta = ""
    if cover:
        cover_item = (
            f'    <item id="cover-image" href="images/cover{cover.extension}" '
            f'media-type="{cover.media_type}" properties="cover-image"/>\n'
        )
        cover_meta = '    <meta name="cover" content="cover-image"/>\n'

    chapter_items = "\n".join(
        f'    <item id="chapter-{index:04d}" href="{file_name}" '
        'media-type="application/xhtml+xml"/>'
        for index, file_name in enumerate(chapter_files, start=1)
    )
    chapter_spine = "\n".join(
        f'    <itemref idref="chapter-{index:04d}"/>'
        for index in range(1, len(chapters) + 1)
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">{book_id}</dc:identifier>
    <dc:title>{escape(novel.title)} - {escape(volume.title)}</dc:title>
    <dc:creator>{creator}</dc:creator>
    <dc:language>pt-BR</dc:language>
    <dc:publisher>{GENERATOR_NAME}</dc:publisher>
    <dc:description>{description}</dc:description>
{subject_tags}
    <meta property="dcterms:modified">{modified}</meta>
    <meta property="schema:accessMode">textual</meta>
    <meta property="schema:accessibilityFeature">tableOfContents</meta>
    <meta name="generator" content="{GENERATOR_NAME}"/>
{cover_meta}  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="css" href="styles/book.css" media-type="text/css"/>
    <item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>
    <item id="metadata" href="metadata.xhtml" media-type="application/xhtml+xml"/>
    <item id="signature" href="signature.xhtml" media-type="application/xhtml+xml"/>
{cover_item}{chapter_items}
  </manifest>
  <spine toc="toc">
    <itemref idref="title"/>
    <itemref idref="metadata"/>
{chapter_spine}
    <itemref idref="signature"/>
  </spine>
</package>
"""


def _title_page(novel: Novel, volume: Volume, cover_href: str | None) -> str:
    cover = (
        f'<img class="cover" src="{cover_href}" alt="Capa de {escape(novel.title)}"/>'
        if cover_href
        else ""
    )
    author = novel.metadata.author or "Autor desconhecido"
    return _xhtml(
        f"{escape(novel.title)} - {escape(volume.title)}",
        f"""
        <section class="title-page">
          {cover}
          <h1>{escape(novel.title)}</h1>
          <p class="subtitle">{escape(volume.title)}</p>
          <p class="byline">{escape(author)}</p>
        </section>
        """,
    )


def _metadata_page(novel: Novel) -> str:
    metadata = novel.metadata
    rows = [
        ("Autor", metadata.author),
        ("Status", metadata.status),
        ("Tipo", metadata.novel_type),
        ("Lançamento", metadata.release_year),
        ("Postado em", metadata.posted_at),
        ("Atualizado em", metadata.updated_at),
        ("Fonte", novel.url),
    ]
    table_rows = "\n".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
        for label, value in rows
        if value
    )
    genres = ", ".join(metadata.genres)
    genre_block = f"<p><strong>Generos:</strong> {escape(genres)}</p>" if genres else ""
    description = f"<p>{escape(metadata.description)}</p>" if metadata.description else ""
    return _xhtml(
        "Metadados",
        f"""
        <section>
          <h1>Sobre esta edição</h1>
          <table>{table_rows}</table>
          {genre_block}
          <h2>Sinopse</h2>
          {description}
        </section>
        """,
    )


def _signature_page(novel: Novel) -> str:
    return _xhtml(
        "Assinatura",
        f"""
        <section class="signature">
          <h1>Assinatura da edição</h1>
          <p>Este EPUB foi estruturado e gerado com {GENERATOR_NAME}.</p>
          <p>Fonte original: {escape(novel.url)}</p>
        </section>
        """,
    )


def _chapter_page(chapter: ChapterContent) -> str:
    return _xhtml(
        chapter.title,
        f"""
        <article class="chapter">
          <h1>{escape(chapter.title)}</h1>
          {chapter.html}
        </article>
        """,
        css_href="../styles/book.css",
    )


def _nav_page(
    novel: Novel,
    volume: Volume,
    chapters: list[ChapterContent],
    chapter_files: list[str],
) -> str:
    chapter_items = "\n".join(
        f'<li><a href="{file_name}">{escape(chapter.title)}</a></li>'
        for chapter, file_name in zip(chapters, chapter_files, strict=True)
    )
    return _xhtml(
        "Sumario",
        f"""
        <nav epub:type="toc" id="toc">
          <h1>{escape(novel.title)} - {escape(volume.title)}</h1>
          <ol>
            <li><a href="title.xhtml">Capa</a></li>
            <li><a href="metadata.xhtml">Sobre esta edição</a></li>
            {chapter_items}
            <li><a href="signature.xhtml">Assinatura da edição</a></li>
          </ol>
        </nav>
        """,
    )


def _toc_ncx(
    book_id: str,
    novel: Novel,
    volume: Volume,
    chapters: list[ChapterContent],
    chapter_files: list[str],
) -> str:
    nav_points = "\n".join(
        f"""
    <navPoint id="chapter-{index:04d}" playOrder="{index + 2}">
      <navLabel><text>{escape(chapter.title)}</text></navLabel>
      <content src="{file_name}"/>
    </navPoint>"""
        for index, (chapter, file_name) in enumerate(
            zip(chapters, chapter_files, strict=True),
            start=1,
        )
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{escape(novel.title)} - {escape(volume.title)}</text></docTitle>
  <navMap>
    <navPoint id="title" playOrder="1">
      <navLabel><text>Capa</text></navLabel>
      <content src="title.xhtml"/>
    </navPoint>
    <navPoint id="metadata" playOrder="2">
      <navLabel><text>Sobre esta edição</text></navLabel>
      <content src="metadata.xhtml"/>
    </navPoint>
{nav_points}
  </navMap>
</ncx>
"""


def _xhtml(title: str, body: str, css_href: str = "styles/book.css") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="pt-BR">
  <head>
    <title>{escape(title)}</title>
    <link rel="stylesheet" type="text/css" href="{css_href}"/>
  </head>
  <body>
    {body}
  </body>
</html>
"""


def _book_css() -> str:
    return """
body {
  font-family: serif;
  line-height: 1.55;
  margin: 5%;
}

h1, h2, h3 {
  font-family: sans-serif;
  line-height: 1.2;
}

p {
  margin: 0 0 1em;
  text-align: justify;
  text-indent: 1.2em;
}

table {
  border-collapse: collapse;
  margin: 1.5em 0;
  width: 100%;
}

th, td {
  border-bottom: 1px solid #d8d8d8;
  padding: 0.35em 0;
  text-align: left;
  vertical-align: top;
}

.title-page {
  text-align: center;
}

.cover {
  display: block;
  margin: 0 auto 2em;
  max-height: 80vh;
  max-width: 100%;
}

.subtitle,
.byline {
  text-align: center;
  text-indent: 0;
}

.chapter h1 {
  margin-bottom: 2em;
  text-align: center;
}

.signature {
  border-top: 1px solid #d8d8d8;
  margin-top: 4em;
  padding-top: 2em;
}
"""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "livro"
