from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from webnovel2kindle.models import Chapter, Novel


def render_novel(novel: Novel, console: Console | None = None, show_chapters: bool = False) -> None:
    console = console or Console()
    summary = (
        f"[bold]{novel.title}[/bold]\n"
        f"[dim]{novel.url}[/dim]\n\n"
        f"{len(novel.volumes)} volume(s) • {novel.chapter_count} capitulo(s)"
    )
    console.print(Panel(summary, border_style="cyan", padding=(1, 2)))

    if not show_chapters:
        _render_volume_table(novel, console)
        return

    tree = Tree("[bold cyan]Estrutura[/bold cyan]")
    for volume in novel.volumes:
        volume_node = tree.add(f"[bold]{volume.title}[/bold] [dim]({len(volume.chapters)})[/dim]")
        for chapter in volume.chapters:
            prefix = f"{chapter.number}. " if chapter.number is not None else ""
            volume_node.add(f"{prefix}{chapter.title}")

    console.print(tree)


def _render_volume_table(novel: Novel, console: Console) -> None:
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Volume", style="bold")
    table.add_column("Capitulos", justify="right")
    table.add_column("Intervalo")
    table.add_column("Primeiro")
    table.add_column("Ultimo")

    for volume in novel.volumes:
        first = volume.chapters[0] if volume.chapters else None
        last = volume.chapters[-1] if volume.chapters else None
        table.add_row(
            volume.title,
            str(len(volume.chapters)),
            _chapter_range(first, last),
            _short_title(first),
            _short_title(last),
        )

    console.print(table)
    console.print("[dim]Use --chapters para listar todos os capitulos.[/dim]")


def _chapter_range(first: Chapter | None, last: Chapter | None) -> str:
    if not first or not last:
        return "-"
    if first.number is None or last.number is None:
        return "-"
    return f"{first.number}-{last.number}"


def _short_title(chapter: Chapter | None, limit: int = 52) -> str:
    if not chapter:
        return "-"
    if len(chapter.title) <= limit:
        return chapter.title
    return f"{chapter.title[: limit - 1].rstrip()}…"
