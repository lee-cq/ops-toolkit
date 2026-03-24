"""
组件控制 CLI 命令 — keepalive / reminder / clipboard
"""
import typer

from ops_toolkit.cli.client import CLIClient, ServerNotRunningError, CLIClientError

component_cmd = typer.Typer(help="组件控制")


# ============ Keepalive ============
keepalive_cmd = typer.Typer(help="保活控制")
component_cmd.add_typer(keepalive_cmd, name="keepalive")


@keepalive_cmd.command("status")
def keepalive_status():
    """查看保活状态"""
    client = CLIClient()
    try:
        data = client.get("/api/keepalive/status")
        running = data.get("running", False)
        status_str = typer.style("ON", fg=typer.colors.GREEN) if running else typer.style("OFF", fg=typer.colors.RED)
        typer.echo(f"Keepalive: {status_str}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@keepalive_cmd.command("on")
def keepalive_on():
    """开启保活"""
    client = CLIClient()
    try:
        data = client.post("/api/keepalive/on")
        typer.echo(data.get("message", "Keepalive started"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@keepalive_cmd.command("off")
def keepalive_off():
    """关闭保活"""
    client = CLIClient()
    try:
        data = client.post("/api/keepalive/off")
        typer.echo(data.get("message", "Keepalive stopped"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# ============ Reminder ============
reminder_cmd = typer.Typer(help="整点提醒控制")
component_cmd.add_typer(reminder_cmd, name="reminder")


@reminder_cmd.command("status")
def reminder_status():
    """查看整点提醒状态"""
    client = CLIClient()
    try:
        data = client.get("/api/reminder/status")
        active = data.get("active", False)
        next_hour = data.get("next_hour", "")
        status_str = typer.style("ON", fg=typer.colors.GREEN) if active else typer.style("OFF", fg=typer.colors.RED)
        typer.echo(f"Hourly Reminder: {status_str}")
        if next_hour:
            typer.echo(f"Next reminder:   {next_hour}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@reminder_cmd.command("on")
def reminder_on(after: int = typer.Option(1, "--after", "-a", help="N 小时后开始提醒")):
    """开启整点提醒"""
    client = CLIClient()
    try:
        data = client.post(f"/api/reminder/on?after={after}")
        typer.echo(data.get("message", "Hourly reminder started"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@reminder_cmd.command("off")
def reminder_off():
    """关闭整点提醒"""
    client = CLIClient()
    try:
        data = client.post("/api/reminder/off")
        typer.echo(data.get("message", "Hourly reminder stopped"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# ============ Clipboard ============
clipboard_cmd = typer.Typer(help="剪贴板监控控制")
component_cmd.add_typer(clipboard_cmd, name="clipboard")


@clipboard_cmd.command("status")
def clipboard_status():
    """查看剪贴板监控状态"""
    client = CLIClient()
    try:
        data = client.get("/api/clipboard/status")
        running = data.get("running", False)
        auto_sls = data.get("auto_sls", False)
        status_str = typer.style("ON", fg=typer.colors.GREEN) if running else typer.style("OFF", fg=typer.colors.RED)
        auto_sls_str = typer.style("ON", fg=typer.colors.GREEN) if auto_sls else typer.style("OFF", fg=typer.colors.RED)
        typer.echo(f"Clipboard Monitor: {status_str}")
        typer.echo(f"Auto SLS Split:    {auto_sls_str}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@clipboard_cmd.command("on")
def clipboard_on():
    """开启剪贴板监控"""
    client = CLIClient()
    try:
        data = client.post("/api/clipboard/on")
        typer.echo(data.get("message", "Clipboard monitoring started"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@clipboard_cmd.command("off")
def clipboard_off():
    """关闭剪贴板监控"""
    client = CLIClient()
    try:
        data = client.post("/api/clipboard/off")
        typer.echo(data.get("message", "Clipboard monitoring stopped"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@clipboard_cmd.command("auto-sls")
def clipboard_auto_sls(
    on_off: str = typer.Argument(help="on 或 off"),
):
    """开关自动日志分割"""
    client = CLIClient()
    try:
        if on_off.lower() == "on":
            data = client.post("/api/clipboard/auto-sls/on")
        elif on_off.lower() == "off":
            data = client.post("/api/clipboard/auto-sls/off")
        else:
            typer.echo("Usage: clipboard auto-sls on|off", err=True)
            raise typer.Exit(1)
        typer.echo(data.get("message", "Updated"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@clipboard_cmd.command("history")
def clipboard_history(limit: int = typer.Option(50, "--limit", "-l", help="显示数量")):
    """查看剪贴板历史"""
    client = CLIClient()
    try:
        data = client.get(f"/api/clipboard/history?limit={limit}")
        records = data.get("records", [])
        if not records:
            typer.echo("No clipboard history.")
            return
        for r in records:
            text = r.get("text", "")
            if len(text) > 80:
                text = text[:80] + "..."
            typer.echo(f"  [{r.get('time', '')}] [{r.get('type', '')}] {text}")
        typer.echo(f"\nTotal: {len(records)} records")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
