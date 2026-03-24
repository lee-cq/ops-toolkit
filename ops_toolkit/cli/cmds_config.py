"""
配置管理 CLI 命令 — show / get / set
"""
import typer

from ops_toolkit.cli.client import CLIClient, ServerNotRunningError, CLIClientError

config_cmd = typer.Typer(help="配置管理")


@config_cmd.command("show")
def config_show():
    """显示完整配置"""
    client = CLIClient()
    try:
        data = client.get("/api/config")
        for key, value in data.items():
            typer.echo(f"  {key:25s} = {value}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@config_cmd.command("get")
def config_get(key: str):
    """获取指定配置项"""
    client = CLIClient()
    try:
        data = client.get(f"/api/config/{key}")
        typer.echo(f"{data['key']} = {data['value']}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@config_cmd.command("set")
def config_set(key: str, value: str):
    """修改配置项并保存"""
    client = CLIClient()
    try:
        # 尝试将 value 转换为合适的类型
        import json
        try:
            typed_value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            typed_value = value

        data = client.put(f"/api/config/{key}", json_data={"value": typed_value})
        typer.echo(data.get("message", "Config updated"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
