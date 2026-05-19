import zipfile
from pathlib import Path

from webnovel2kindle.epub import build_epub
from webnovel2kindle.models import Chapter, ChapterContent, Novel, NovelMetadata, Volume


def test_build_epub_writes_professional_book_structure(tmp_path: Path) -> None:
    volume = Volume(
        title="Volume 1",
        chapters=(Chapter(title="Capitulo 1", url="https://centralnovel.com/cap-1/", number=1),),
    )
    novel = Novel(
        title="Shadow Slave",
        url="https://centralnovel.com/series/shadow-slave-20230928/",
        volumes=(volume,),
        metadata=NovelMetadata(
            author="Guiltythree",
            status="Em andamento",
            novel_type="Webnovel",
            release_year="2022",
            description="Uma sinopse elegante.",
            genres=("Fantasia", "Ação"),
        ),
    )
    output_path = tmp_path / "shadow-slave-volume-1.epub"

    build_epub(
        novel,
        volume,
        [ChapterContent(title="Capitulo 1", html="<p>Texto do capitulo.</p>")],
        output_path,
    )

    with zipfile.ZipFile(output_path) as epub:
        names = epub.namelist()
        assert names[0] == "mimetype"
        assert "META-INF/container.xml" in names
        assert "OEBPS/content.opf" in names
        assert "OEBPS/nav.xhtml" in names
        assert "OEBPS/title.xhtml" in names
        assert "OEBPS/metadata.xhtml" in names
        assert "OEBPS/signature.xhtml" in names
        assert "OEBPS/chapters/chapter-0001.xhtml" in names

        opf = epub.read("OEBPS/content.opf").decode()
        signature = epub.read("OEBPS/signature.xhtml").decode()
        chapter = epub.read("OEBPS/chapters/chapter-0001.xhtml").decode()

    assert "<dc:creator>Guiltythree</dc:creator>" in opf
    assert "<dc:subject>Fantasia</dc:subject>" in opf
    assert "webnovel2kindle" in signature
    assert "../styles/book.css" in chapter
