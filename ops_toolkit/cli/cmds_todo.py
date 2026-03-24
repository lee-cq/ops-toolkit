"""
待办事项 CLI 命令 — list / get / add / update / complete / delete
"""
import typer

from ops_toolkit.cli.client import CLIClient, ServerNotRunningError, CLIClientError

todo_cmd = typer.Typer(help="待办事项管理")


@todo_cmd.command("list")
def todo_list(
    status: int = typer.Option(None, "--status", "-s", help="状态过滤: 0=进行中 1=已完成 2=已取消"),
    limit: int = typer.Option(50, "--limit", "-l", help="显示数量"),
):
    """列出任务"""
    client = CLIClient()
    try:
        params = {"limit": limit}
        if status is not None:
            params["status"] = status
        data = client.get("/api/todo/list", params=params)
        tasks = data.get("tasks", [])
        if not tasks:
            typer.echo("No tasks found.")
            return

        status_map = {0: "进行中", 1: "已完成", 2: "已取消"}
        for t in tasks:
            status_str = status_map.get(t.get("status", 0), "未知")
            title = t.get("title", "")
            tid = t.get("id", 0)
            do_time = t.get("do_time", "")
            if do_time and do_time != "None":
                title += f"  [due: {do_time}]"
            typer.echo(f"  [{tid:3d}] [{status_str}] {title}")
        typer.echo(f"\nTotal: {len(tasks)} tasks")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@todo_cmd.command("get")
def todo_get(task_id: int):
    """查看任务详情"""
    client = CLIClient()
    try:
        data = client.get(f"/api/todo/{task_id}")
        status_map = {0: "进行中", 1: "已完成", 2: "已取消"}
        typer.echo(f"ID:          {data.get('id')}")
        typer.echo(f"Title:       {data.get('title')}")
        typer.echo(f"Status:      {status_map.get(data.get('status', 0), '未知')}")
        typer.echo(f"Description: {data.get('desc') or '(empty)'}")
        typer.echo(f"Link:        {data.get('link') or '(empty)'}")
        typer.echo(f"Created:     {data.get('create_time')}")
        typer.echo(f"Do time:     {data.get('do_time') or '(not set)'}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@todo_cmd.command("add")
def todo_add(
    title: str = typer.Argument(help="任务标题"),
    desc: str = typer.Option("", "--desc", "-d", help="任务描述"),
    link: str = typer.Option("", "--link", help="关联链接"),
):
    """添加新任务"""
    client = CLIClient()
    try:
        body = {"title": title}
        if desc:
            body["desc"] = desc
        if link:
            body["link"] = link
        data = client.post("/api/todo", json_data=body)
        typer.echo(f"Task created: ID={data.get('id')}")
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@todo_cmd.command("update")
def todo_update(
    task_id: int = typer.Argument(help="任务 ID"),
    title: str = typer.Option(None, "--title", "-t", help="新标题"),
    desc: str = typer.Option(None, "--desc", "-d", help="新描述"),
    status: int = typer.Option(None, "--status", "-s", help="新状态: 0=进行中 1=已完成 2=已取消"),
):
    """更新任务"""
    client = CLIClient()
    try:
        body = {}
        if title is not None:
            body["title"] = title
        if desc is not None:
            body["desc"] = desc
        if status is not None:
            body["status"] = status
        if not body:
            typer.echo("Nothing to update. Use --title, --desc, or --status.", err=True)
            raise typer.Exit(1)
        data = client.put(f"/api/todo/{task_id}", json_data=body)
        typer.echo(data.get("message", "Task updated"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@todo_cmd.command("complete")
def todo_complete(task_id: int):
    """完成任务"""
    client = CLIClient()
    try:
        data = client.put(f"/api/todo/{task_id}", json_data={"status": 1})
        typer.echo(data.get("message", f"Task {task_id} completed"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@todo_cmd.command("delete")
def todo_delete(task_id: int):
    """删除任务"""
    client = CLIClient()
    try:
        data = client.delete(f"/api/todo/{task_id}")
        typer.echo(data.get("message", f"Task {task_id} deleted"))
    except ServerNotRunningError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except CLIClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
