"""
Run this to process poems. These are cached on Headwater server, so this frontloads work.
"""

from trmnl.engines.poems.process import process_poem, Poem
from trmnl.engines.poems.poem import filter_poems
from rich.console import Console
from conduit.progress.verbosity import Verbosity

VERBOSITY = Verbosity.SILENT
console = Console()
poem_list = filter_poems()
poems = [Poem(**poem) for poem in poem_list]


def run_background_process():
    for index, poem in enumerate(poems):
        console.print(f"[blue]Processing poem {index + 1} of {len(poems)}[/blue]")
        processed_poem = process_poem(poem, verbose=VERBOSITY)
        if processed_poem:
            console.print(
                f"\t[green]Processed poem:[/green] [cyan]{poem.title} by {poem.poet}[/cyan]"
            )
        else:
            console.print(
                f"\t[yellow]Skipped poem:[/yellow] [cyan]{poem.title} by {poem.poet}[/cyan]"
            )


if __name__ == "__main__":
    run_background_process()
