"""
应用级 CLI 命令 — status / version / quit
"""
import sys

import typer

from ops_toolkit.cli.client import CLIClient, ServerNotRunningError, CLIClientError

app_cmd = typer.Typer(help="应用状态管理")


@app_cmd.command()
def status():
    """查看主程序运行状态"""
    client = CLIClient()
    try:
        data = client.get("/api/status")
        typer.echo(f"App:    {data.get('app_name', 'unknown')}")
        typer.echo(f"Version:{data.get('version', 'unknown')}")
        typer.echo(f"Status: {'running' if data.get('running') else 'stopped'}")

        components = data.get("components", {})
        typer.echo("\nComponents:")
        for name, running in components.items():
            status_str = typer.style("ON ", fg=typer.colors.GREEN) if running else typer.style("OFF", fg=typer.colors.RED)
            typer.echo(f"  {name:20s} {status_str}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app_cmd.command()
def quit():
    """退出主程序"""
    client = CLIClient()
    try:
        data = client.post("/api/quit")
        typer.echo(data.get("message", "Quit signal sent"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
