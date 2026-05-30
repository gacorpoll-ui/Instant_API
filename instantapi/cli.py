"""Main CLI entrypoint for InstantAPI."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Force UTF-8 encoding for standard streams on Windows to support emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from instantapi.config import (
    Config,
    LLMProvider,
    PROVIDER_ENV_KEYS,
    PROVIDER_MODELS,
)

app = typer.Typer(
    name="instantapi",
    help="⚡ Turn any website into a REST API in 30 seconds.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _run(coro):
    """Run async coroutine from sync context."""
    return asyncio.run(coro)


def _banner():
    console.print(
        Panel.fit(
            "[bold cyan]⚡ InstantAPI[/bold cyan]\n"
            "[dim]Turn any website into a REST API[/dim]",
            border_style="cyan",
        )
    )


# ─── Commands ────────────────────────────────────────────────────────────────


@app.command()
def init():
    """[bold]Set up InstantAPI[/bold] — choose your LLM provider."""
    _banner()
    console.print("\n[bold]Setup Wizard[/bold] — Let's configure your LLM provider.\n")

    # Provider selection
    providers = [p.value for p in LLMProvider]
    for i, p in enumerate(providers, 1):
        model = PROVIDER_MODELS.get(p, "")  # type: ignore[call-overload]
        console.print(f"  [cyan]{i}[/cyan]. [bold]{p}[/bold]  [dim]({model})[/dim]")

    choice = Prompt.ask(
        "\nChoose provider [1-{}]".format(len(providers)),
        default="1",
    )

    try:
        idx = int(choice) - 1
        provider = LLMProvider(providers[idx])
    except (ValueError, IndexError):
        console.print("[red]Invalid choice. Defaulting to Ollama.[/red]")
        provider = LLMProvider.OLLAMA

    config = Config(provider=provider)

    # API key if needed
    env_key = PROVIDER_ENV_KEYS.get(provider)
    if env_key:
        api_key = Prompt.ask(
            f"Enter your [cyan]{env_key}[/cyan]",
            default="",
            password=True,
        )
        config.api_key = api_key

    # Custom model (optional)
    default_model = PROVIDER_MODELS.get(provider, "")  # type: ignore[call-overload]
    custom_model = Prompt.ask(
        f"Model to use [dim](default: {default_model})[/dim]",
        default=default_model,
    )
    config.model = custom_model

    config.save()
    console.print(
        f"\n[green]✅ Config saved![/green]  "
        f"Provider: [bold]{provider.value}[/bold]  "
        f"Model: [bold]{config.model}[/bold]\n"
    )


@app.command()
def scrape(
    url: str = typer.Argument(..., help="URL to scrape and turn into an API"),
    extract: Optional[str] = typer.Option(
        None,
        "--extract",
        "-e",
        help="Natural language query for specific data extraction",
    ),
    port: int = typer.Option(3000, "--port", "-p", help="Port to run the API server on"),
    export: Optional[str] = typer.Option(
        None,
        "--export",
        "-o",
        help="Export project to directory instead of starting live server",
    ),
    no_serve: bool = typer.Option(
        False,
        "--no-serve",
        help="Detect schema only, save to DB, don't start server",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="Override LLM provider (ollama/openai/anthropic/gemini/groq)",
    ),
):
    """[bold]Scrape a website[/bold] and generate a REST API instantly."""
    _run(_scrape_async(url, extract, port, export, no_serve, provider))


async def _scrape_async(
    url: str,
    extract: Optional[str],
    port: int,
    export: Optional[str],
    no_serve: bool,
    provider_override: Optional[str],
):
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    from instantapi.ai.detector import detect_schema
    from instantapi.api.exporter import export_project
    from instantapi.api.server import run_server
    from instantapi.scraper.browser import BrowserScraper
    from instantapi.storage.db import save_api

    config = Config.load()

    # Override provider if specified
    if provider_override:
        try:
            config.provider = LLMProvider(provider_override.lower())
            config.model = PROVIDER_MODELS.get(config.provider, config.model)  # type: ignore[call-overload]
        except ValueError:
            console.print(f"[red]Unknown provider: {provider_override}[/red]")
            raise typer.Exit(1)

    _banner()
    console.print(f"[bold]Scraping:[/bold] [cyan]{url}[/cyan]")
    if extract:
        console.print(f"[bold]Query:[/bold] [yellow]{extract}[/yellow]")
    console.print(
        f"[dim]Provider: {config.provider.value}  Model: {config.model}[/dim]\n"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Step 1: Scrape
        t1 = progress.add_task("[cyan]Scraping page...", total=None)
        async with BrowserScraper(timeout=config.timeout) as scraper:
            page = await scraper.scrape(url)
        progress.update(t1, description="[green]✅ Page scraped")
        progress.stop_task(t1)

        # Step 2: AI detection
        t2 = progress.add_task("[cyan]Detecting schema with AI...", total=None)
        result = await detect_schema(page, config, extract_query=extract)
        result.source_url = url
        progress.update(t2, description="[green]✅ Schema detected")
        progress.stop_task(t2)

        # Step 3: Save to DB
        t3 = progress.add_task("[cyan]Saving to database...", total=None)
        api_id = await save_api(result)
        progress.update(t3, description=f"[green]✅ Saved (id={api_id})")
        progress.stop_task(t3)

    # Show results
    console.print()
    console.print(Panel(
        f"[bold green]🎉 API Ready![/bold green]\n\n"
        f"[bold]Site:[/bold] {result.site_description or url}\n"
        f"[bold]Endpoints:[/bold] {len(result.endpoints)} detected",
        border_style="green",
    ))

    # Show endpoint table
    if result.endpoints:
        table = Table(title="Detected Endpoints", show_header=True)
        table.add_column("Endpoint", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Items", style="yellow")
        table.add_column("Fields", style="dim")
        for ep in result.endpoints:
            table.add_row(
                f"GET /api/{ep.name}",
                ep.description[:60] + ("…" if len(ep.description) > 60 else ""),
                str(ep.item_count),
                ", ".join(list(ep.schema_fields.keys())[:5]),
            )
        console.print(table)
        console.print()

    if export:
        # Export mode
        output_path = export_project(result, export)
        console.print(f"[bold green]✅ Project exported to:[/bold green] {output_path}")
        console.print(f"[dim]Run: cd {export} && uvicorn main:app --reload[/dim]")

    elif not no_serve:
        # Live server mode
        console.print(
            f"[bold green]🚀 Starting API server on port {port}...[/bold green]\n"
            f"  [cyan]API:[/cyan]  http://localhost:{port}/\n"
            f"  [cyan]Docs:[/cyan] http://localhost:{port}/docs\n"
        )
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        run_server(result, port=port)
    else:
        console.print(f"[green]✅ Schema saved with id={api_id}. Run `instantapi serve {api_id}` to start.[/green]")


@app.command(name="list")
def list_apis_cmd():
    """[bold]List[/bold] all saved APIs."""
    _run(_list_async())


async def _list_async():
    from instantapi.storage.db import list_apis

    apis = await list_apis()

    if not apis:
        console.print("[yellow]No saved APIs found.[/yellow]  Run [cyan]instantapi scrape <url>[/cyan] first.")
        return

    table = Table(title="Saved APIs", show_header=True, show_lines=True)
    table.add_column("ID", style="cyan", width=6)
    table.add_column("URL", style="white")
    table.add_column("Description", style="dim")
    table.add_column("Created", style="dim")

    for api in apis:
        table.add_row(
            str(api["id"]),
            api["url"][:60],
            (api.get("site_description") or "")[:40],
            api["created_at"][:19].replace("T", " "),
        )
    console.print(table)


@app.command()
def serve(
    api_id: int = typer.Argument(..., help="API ID to serve (from `instantapi list`)"),
    port: int = typer.Option(3000, "--port", "-p", help="Port to serve on"),
):
    """[bold]Serve[/bold] a previously saved API."""
    _run(_serve_async(api_id, port))


async def _serve_async(api_id: int, port: int):
    from instantapi.api.server import run_server
    from instantapi.storage.db import get_api

    result = await get_api(api_id)
    if not result:
        console.print(f"[red]API with id={api_id} not found.[/red]")
        raise typer.Exit(1)

    _banner()
    console.print(
        f"[bold green]🚀 Serving API #{api_id}[/bold green]\n"
        f"  [cyan]Source:[/cyan] {result.source_url}\n"
        f"  [cyan]API:[/cyan]    http://localhost:{port}/\n"
        f"  [cyan]Docs:[/cyan]   http://localhost:{port}/docs\n"
    )
    run_server(result, port=port)


@app.command()
def export(
    api_id: int = typer.Argument(..., help="API ID to export"),
    output: str = typer.Argument(..., help="Output directory path"),
):
    """[bold]Export[/bold] a saved API as a deployable FastAPI project."""
    _run(_export_async(api_id, output))


async def _export_async(api_id: int, output: str):
    from instantapi.api.exporter import export_project
    from instantapi.storage.db import get_api

    result = await get_api(api_id)
    if not result:
        console.print(f"[red]API with id={api_id} not found.[/red]")
        raise typer.Exit(1)

    out_path = export_project(result, output)
    console.print(f"[bold green]✅ Project exported to:[/bold green] {out_path}")
    console.print(f"[dim]Run: cd {output} && pip install -r requirements.txt && uvicorn main:app[/dim]")


@app.command()
def delete(
    api_id: int = typer.Argument(..., help="API ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """[bold]Delete[/bold] a saved API."""
    _run(_delete_async(api_id, yes))


async def _delete_async(api_id: int, yes: bool):
    from instantapi.storage.db import delete_api

    if not yes and not Confirm.ask(f"Delete API #{api_id}?"):
        return

    ok = await delete_api(api_id)
    if ok:
        console.print(f"[green]✅ API #{api_id} deleted.[/green]")
    else:
        console.print(f"[red]API #{api_id} not found.[/red]")


def config_cmd(
    provider: Optional[str] = typer.Option(None, "--provider", help="Set LLM provider"),
    model: Optional[str] = typer.Option(None, "--model", help="Set model name"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Set API key"),
    api_base: Optional[str] = typer.Option(None, "--api-base", help="Set custom API base URL"),
    port: Optional[int] = typer.Option(None, "--port", help="Set default server port"),
    show: bool = typer.Option(False, "--show", help="Show current config"),
):
    """[bold]Configure[/bold] InstantAPI settings."""
    cfg = Config.load()

    if show or not any([provider, model, api_key, api_base, port]):
        table = Table(title="Current Config", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Provider", cfg.provider.value)
        table.add_row("Model", cfg.model)
        table.add_row("API Key", "***" if cfg.api_key else "(not set)")
        table.add_row("API Base", cfg.api_base or "(default)")
        table.add_row("Default Port", str(cfg.api_port))
        table.add_row("Max Pages", str(cfg.max_pages))
        table.add_row("Timeout (s)", str(cfg.timeout))
        console.print(table)
        return

    if provider:
        try:
            cfg.provider = LLMProvider(provider.lower())
        except ValueError:
            console.print(f"[red]Unknown provider: {provider}[/red]")
            raise typer.Exit(1)

    if model:
        cfg.model = model
    if api_key:
        cfg.api_key = api_key
    if api_base:
        cfg.api_base = api_base
    if port:
        cfg.api_port = port

    cfg.save()
    console.print("[green]✅ Config saved.[/green]")


@app.command()
def dashboard(
    port: int = typer.Option(8765, "--port", "-p", help="Port to run the dashboard on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
):
    """[bold]Start the Web Dashboard[/bold] to manage saved APIs."""
    from instantapi.dashboard.app import run_dashboard
    _banner()
    console.print(
        f"[bold green]🚀 Starting Web Dashboard...[/bold green]\n"
        f"  [cyan]Dashboard:[/cyan] http://{host}:{port}/\n"
    )
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    run_dashboard(host=host, port=port)


# Alias for `config` command
app.command(name="config")(config_cmd)


if __name__ == "__main__":
    app()
