from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .generator import GenerationConfig, generate_and_write
from .validator import validate_output


app = typer.Typer(add_completion=False, help="Synthetic field-service seed data generator")
console = Console()


@app.command()
def generate(
    clients: int = typer.Option(10, min=1, help="Number of clients to generate"),
    projects: int = typer.Option(30, min=1, help="Number of projects to generate"),
    tickets: int = typer.Option(200, min=1, help="Number of tickets to generate"),
    seed: int = typer.Option(42, help="Random seed"),
    output_dir: Path = typer.Option(Path("output"), help="Output directory"),
) -> None:
    config = GenerationConfig(clients=clients, projects=projects, tickets=tickets, seed=seed, output_dir=output_dir)
    _, issues = generate_and_write(config)
    if issues:
        console.print("\n".join(issues))
        raise typer.Exit(code=1)
    console.print(f"Generated dataset in {output_dir.resolve()}")


@app.command()
def validate(output_dir: Path = typer.Option(Path("output"), help="Output directory")) -> None:
    issues = validate_output(output_dir)
    if issues:
        for issue in issues:
            console.print(issue.format())
        raise typer.Exit(code=1)
    console.print(f"Validation passed for {output_dir.resolve()}")


def main() -> None:
    app()

