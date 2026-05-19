from __future__ import annotations

from urllib.parse import urlparse

import typer
from rich.console import Console

from webnovel2kindle.rendering.console import render_novel
from webnovel2kindle.scraper.centralnovel import parse_novel_page
from webnovel2kindle.scraper.client import FetchError, HttpClient

app = typer.Typer(help="Mapeia obras da Central Novel para futura geracao de EPUB.")
console = Console()


@app.callback()
def main() -> None:
    """Mapeia obras da Central Novel para futura geracao de EPUB."""


@app.command()
def scan(
    url: str | None = typer.Argument(None, help="URL da pagina da obra na Central Novel."),
    chapters: bool = typer.Option(
        False,
        "--chapters",
        help="Lista todos os capitulos encontrados.",
    ),
) -> None:
    """Busca a obra e exibe volumes/capitulos encontrados."""
    novel_url = url or typer.prompt("Link da obra")

    if not _is_centralnovel_url(novel_url):
        console.print("[red]Por enquanto a CLI aceita apenas links da Central Novel.[/red]")
        raise typer.Exit(code=1)

    try:
        html = HttpClient().get_html(novel_url)
    except FetchError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    novel = parse_novel_page(html, novel_url)
    render_novel(novel, console, show_chapters=chapters)


def _is_centralnovel_url(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname == "centralnovel.com" or hostname.endswith(".centralnovel.com")


if __name__ == "__main__":
    app()
