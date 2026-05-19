from pathlib import Path

from webnovel2kindle.scraper.centralnovel import parse_novel_page

FIXTURE = Path(__file__).parent / "fixtures" / "centralnovel_shadow_slave.html"


def test_parse_novel_page_extracts_title_volumes_and_chapters() -> None:
    html = FIXTURE.read_text()

    novel = parse_novel_page(html, "https://centralnovel.com/series/shadow-slave-20230928/")

    assert novel.title == "Shadow Slave"
    assert novel.chapter_count == 3
    assert [volume.title for volume in novel.volumes] == [
        "Volume 1: Child of Shadows",
        "Volume 2: Demon of Change",
    ]
    assert [chapter.title for chapter in novel.volumes[0].chapters] == [
        "Chapter 1: Nightmare Begins",
        "Chapter 2: Slave Caravan",
    ]
    assert novel.volumes[1].chapters[0].number == 96
    assert novel.volumes[0].chapters[0].url == (
        "https://centralnovel.com/series/shadow-slave-20230928/chapter-1-nightmare-begins/"
    )


def test_parse_novel_page_uses_default_volume_when_no_volume_headings() -> None:
    html = """
    <html>
      <body>
        <h1>Solo Novel</h1>
        <a href="/series/solo/chapter-2/">Chapter 2</a>
        <a href="/series/solo/chapter-1/">Chapter 1</a>
      </body>
    </html>
    """

    novel = parse_novel_page(html, "https://centralnovel.com/series/solo/")

    assert [volume.title for volume in novel.volumes] == ["Capitulos"]
    assert [chapter.number for chapter in novel.volumes[0].chapters] == [1, 2]


def test_parse_novel_page_uses_centralnovel_eplister_blocks() -> None:
    html = """
    <html>
      <body>
        <h1>Shadow Slave</h1>
        <div class="eplister">
          <a href="https://centralnovel.com/shadow-slave-capitulo-4/">
            Vol. 2 Cap. 4 Fourth
          </a>
          <a href="https://centralnovel.com/shadow-slave-capitulo-4/pdf/"></a>
          <a href="https://centralnovel.com/shadow-slave-capitulo-3/">
            Vol. 2 Cap. 3 Third
          </a>
        </div>
        <div class="eplister">
          <a href="https://centralnovel.com/shadow-slave-capitulo-2/">
            Vol. 1 Cap. 2 Second
          </a>
          <a href="https://centralnovel.com/shadow-slave-capitulo-1/">
            Vol. 1 Cap. 1 First
          </a>
        </div>
      </body>
    </html>
    """

    novel = parse_novel_page(html, "https://centralnovel.com/series/shadow-slave-20230928/")

    assert [volume.title for volume in novel.volumes] == ["Volume 1", "Volume 2"]
    assert [chapter.number for chapter in novel.volumes[0].chapters] == [1, 2]
    assert [chapter.number for chapter in novel.volumes[1].chapters] == [3, 4]
    assert novel.chapter_count == 4
