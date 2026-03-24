"""
翻译与历史 CLI 命令 — translate / history
"""
import typer

from ops_toolkit.cli.client import CLIClient, ServerNotRunningError, CLIClientError

translate_cmd = typer.Typer(help="翻译与历史记录")


@translate_cmd.command("translate")
def translate_text(text: str = typer.Argument(help="要翻译的文本")):
    """翻译文本"""
    client = CLIClient()
    try:
        data = client.post("/api/translate", json_data={"text": text})
        typer.echo(f"原文:   {data.get('text', '')}")
        typer.echo(f"翻译:   {data.get('result', '')}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@translate_cmd.command("history")
def translate_history(limit: int = typer.Option(50, "--limit", "-l", help="显示数量")):
    """查看翻译历史记录"""
    client = CLIClient()
    try:
        data = client.get(f"/api/translate/history?limit={limit}")
        records = data.get("records", [])
        if not records:
            typer.echo("No translation history.")
            return
        for r in records:
            src = r.get("src", "")
            dst = r.get("dst", "")
            if len(src) > 60:
                src = src[:60] + "..."
            if len(dst) > 60:
                dst = dst[:60] + "..."
            typer.echo(f"  {src}  →  {dst}")
        typer.echo(f"\nTotal: {len(records)} records")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
