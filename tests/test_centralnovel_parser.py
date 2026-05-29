from pathlib import Path

from webnovel2kindle.scraper.centralnovel import parse_chapter_page, parse_novel_page

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
        <div class="spe">
          <span>Status: Em andamento</span>
          <span>Tipo: Novel Ocidental , Webnovel</span>
          <span>Autor: Guiltythree</span>
          <span>Lançamento: 2022</span>
          <span>Postado em: março 25, 2023</span>
          <span>Atualizado em: maio 15, 2026</span>
        </div>
        <img class="ts-post-image" src="/wp-content/uploads/shadow-slave.png" />
        <div class="genxed">Ação</div>
        <div class="genxed">Fantasia</div>
        <div class="entry-content">
          <p>Crescendo na pobreza, Sunny nunca esperou nada de bom da vida.</p>
          <div>AVISO Este conteúdo foi traduzido automaticamente.</div>
          <hr />
          <p>Se você possui os direitos legais sobre a obra...</p>
          <p>Confira outras músicas de Shadow Slave.</p>
        </div>
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
    assert novel.metadata.author == "Guiltythree"
    assert novel.metadata.status == "Em andamento"
    assert novel.metadata.novel_type == "Novel Ocidental , Webnovel"
    assert novel.metadata.release_year == "2022"
    assert novel.metadata.cover_url == "https://centralnovel.com/wp-content/uploads/shadow-slave.png"
    assert novel.metadata.genres == ("Ação", "Fantasia")
    assert novel.metadata.description == (
        "Crescendo na pobreza, Sunny nunca esperou nada de bom da vida."
    )


def test_parse_novel_page_keeps_textual_eplister_volumes() -> None:
    html = """
    <html>
      <body>
        <h1>Lord of Mysteries</h1>
        <div class="eplister">
          <a href="https://centralnovel.com/lord-of-mysteries-capitulo-1432/">
            <div class="epl-num">Vol. Bonus Cap. 1432 [Fim[</div>
            <div class="epl-title">Capítulo Bônus: Aquele Canto (2)</div>
          </a>
        </div>
        <div class="eplister">
          <a href="https://centralnovel.com/lord-of-mysteries-capitulo-1430/">
            <div class="epl-num">Vol. Side Story 2 Cap. 1430</div>
            <div class="epl-title">Nos Dias Modernos (28)</div>
          </a>
        </div>
        <div class="eplister">
          <a href="https://centralnovel.com/lord-of-mysteries-capitulo-1394/">
            <div class="epl-num">Vol. 8 Cap. 1394</div>
            <div class="epl-title">Uma Nova Jornada</div>
          </a>
        </div>
        <div class="eplister">
          <a href="https://centralnovel.com/lord-of-mysteries-capitulo-1437/">
            <div class="epl-num">Vol. Extra Cap. 1437</div>
            <div class="epl-title">Sempre que Vejo a Lua Cheia</div>
          </a>
        </div>
      </body>
    </html>
    """

    novel = parse_novel_page(html, "https://centralnovel.com/series/lord-of-mysteries-20240505/")

    assert [volume.title for volume in novel.volumes] == [
        "Volume Extra",
        "Volume 8",
        "Volume Side Story 2",
        "Volume Bonus",
    ]
    assert [chapter.number for volume in novel.volumes for chapter in volume.chapters] == [
        1437,
        1394,
        1430,
        1432,
    ]


def test_parse_novel_page_prefers_centralnovel_collapsible_volume_headings() -> None:
    html = """
    <html>
      <body>
        <h1>Lord of Mysteries</h1>
        <span class="ts-chl-collapsible">Volume  Side Story 2</span>
        <div class="ts-chl-collapsible-content">
          <div class="eplister">
            <ul>
              <li>
                <a href="https://centralnovel.com/lord-of-mysteries-capitulo-1430/">
                  <div class="epl-num">Vol. Side Story 2 Cap. 1430</div>
                  <div class="epl-title">Nos Dias Modernos (28)</div>
                  <div class="epl-date">abril 24, 2024</div>
                </a>
              </li>
            </ul>
          </div>
        </div>
        <span class="ts-chl-collapsible">Volume  Bonus</span>
        <div class="ts-chl-collapsible-content">
          <div class="eplister">
            <ul>
              <li>
                <a href="https://centralnovel.com/lord-of-mysteries-capitulo-1432/">
                  <div class="epl-num">Vol. Bonus Cap. 1432 [Fim[</div>
                  <div class="epl-title">Capítulo Bônus: Aquele Canto (2)</div>
                  <div class="epl-date">abril 24, 2024</div>
                </a>
              </li>
            </ul>
          </div>
        </div>
      </body>
    </html>
    """

    novel = parse_novel_page(html, "https://centralnovel.com/series/lord-of-mysteries-20240505/")

    assert [volume.title for volume in novel.volumes] == [
        "Volume Side Story 2",
        "Volume Bonus",
    ]
    assert [chapter.title for volume in novel.volumes for chapter in volume.chapters] == [
        "Vol. Side Story 2 Cap. 1430 Nos Dias Modernos (28)",
        "Vol. Bonus Cap. 1432 [Fim[ Capítulo Bônus: Aquele Canto (2)",
    ]


def test_parse_chapter_page_extracts_clean_xhtml_paragraphs() -> None:
    html = """
    <html>
      <body>
        <h1 class="entry-title">Shadow Slave - Capítulo 1</h1>
        <div class="cat-series">O Pesadelo Começa</div>
        <div class="epcontent">
          <p>Traduzido usando o ChatGPT</p>
          <p>Um jovem & uma xícara de café.</p>
          <script>bad()</script>
        </div>
      </body>
    </html>
    """

    chapter = parse_chapter_page(html)

    assert chapter.title == "Capítulo 1 - O Pesadelo Começa"
    assert "<script>" not in chapter.html
    assert "<p>Um jovem &amp; uma xícara de café.</p>" in chapter.html
