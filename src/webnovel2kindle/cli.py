from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import typer
from rich.console import Console

from webnovel2kindle.epub import build_epub, cover_from_response, epub_file_name
from webnovel2kindle.models import Volume
from webnovel2kindle.rendering.console import render_novel
from webnovel2kindle.scraper.centralnovel import parse_chapter_page, parse_novel_page
from webnovel2kindle.scraper.client import FetchError, HttpClient

app = typer.Typer(
    help="Mapeia obras da Central Novel para futura geracao de EPUB.",
    invoke_without_command=True,
)
console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    url: str | None = typer.Option(None, "--url", "-u", help="URL da obra na Central Novel."),
    volume: int | None = typer.Option(
        None,
        "--volume",
        "-v",
        help="Numero do volume na lista exibida.",
    ),
    output_dir: Path = typer.Option(  # noqa: B008
        "dist",
        "--output-dir",
        "-o",
        help="Pasta de saida.",
    ),
) -> None:
    """Mapeia obras da Central Novel para futura geracao de EPUB."""
    if ctx.invoked_subcommand is None:
        run_flow(url=url, volume=volume, output_dir=output_dir)


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


@app.command()
def export(
    url: str | None = typer.Argument(None, help="URL da pagina da obra na Central Novel."),
    volume: int | None = typer.Option(
        None,
        "--volume",
        "-v",
        help="Numero do volume na lista exibida.",
    ),
    output_dir: Path = typer.Option(  # noqa: B008
        "dist",
        "--output-dir",
        "-o",
        help="Pasta de saida.",
    ),
) -> None:
    """Seleciona um volume e gera um EPUB desse volume."""
    run_flow(url=url, volume=volume, output_dir=output_dir)


def run_flow(url: str | None, volume: int | None, output_dir: Path) -> None:
    """Executa o fluxo completo: link, volumes, escolha, download e EPUB."""
    novel_url = url or typer.prompt("Link da obra")
    if not _is_centralnovel_url(novel_url):
        console.print("[red]Por enquanto a CLI aceita apenas links da Central Novel.[/red]")
        raise typer.Exit(code=1)

    client = HttpClient()
    try:
        html = client.get_html(novel_url)
    except FetchError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    novel = parse_novel_page(html, novel_url)
    render_novel(novel, console)
    selected_volume = _select_volume(novel.volumes, volume)

    console.print(f"[cyan]Baixando {len(selected_volume.chapters)} capitulo(s)...[/cyan]")
    chapters = []
    with console.status("[bold cyan]Preparando EPUB...[/bold cyan]"):
        try:
            for chapter in selected_volume.chapters:
                chapter_html = client.get_html(chapter.url)
                chapters.append(parse_chapter_page(chapter_html))
        except FetchError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc

        cover = None
        if novel.metadata.cover_url:
            try:
                cover_data, content_type = client.get_bytes(novel.metadata.cover_url)
                cover = cover_from_response(cover_data, content_type, novel.metadata.cover_url)
            except FetchError:
                cover = None

        output_path = output_dir / epub_file_name(novel, selected_volume)
        build_epub(novel, selected_volume, chapters, output_path, cover)

    console.print(f"[green]EPUB gerado:[/green] {output_path}")


def _is_centralnovel_url(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname == "centralnovel.com" or hostname.endswith(".centralnovel.com")


def _select_volume(volumes: tuple[Volume, ...], volume: int | None) -> Volume:
    if not volumes:
        console.print("[red]Nenhum volume encontrado.[/red]")
        raise typer.Exit(code=1)

    if volume is None:
        volume = typer.prompt("Escolha o volume", type=int)

    if volume < 1 or volume > len(volumes):
        console.print(f"[red]Volume invalido. Escolha de 1 a {len(volumes)}.[/red]")
        raise typer.Exit(code=1)

    return volumes[volume - 1]


if __name__ == "__main__":
    app()
