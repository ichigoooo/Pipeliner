from __future__ import annotations

from html import escape
from typing import Any


def _page(title: str, body: str) -> str:
    styles = """
          body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                 margin: 24px; color: #111827; }
          h1, h2 { margin-bottom: 12px; }
          table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
          th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }
          th { background: #f3f4f6; }
          code { background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }
          .badge { display: inline-block; padding: 2px 8px;
                   border-radius: 999px; background: #e5e7eb; }
          .attention { background: #fef3c7; }
          pre { background: #111827; color: white; padding: 12px;
                border-radius: 6px; overflow-x: auto; }
          a { color: #2563eb; text-decoration: none; }
    """
    return f"""
    <!doctype html>
    <html lang=\"zh-CN\">
      <head>
        <meta charset=\"utf-8\" />
        <title>{escape(title)}</title>
        <style>{styles}</style>
      </head>
      <body>
        {body}
      </body>
    </html>
    """


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{escape(str(item))}</th>" for item in headers)
    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>" + "".join(f"<td>{escape(str(item))}</td>" for item in row) + "</tr>"
        )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_index(attention_runs: list[dict[str, Any]]) -> str:
    rows = [
        [
            item["run_id"],
            item["workflow_id"],
            item["status"],
            item.get("stop_reason", ""),
        ]
        for item in attention_runs
    ]
    table = (
        _table(["Run", "Workflow", "Status", "Stop Reason"], rows)
        if rows
        else "<p>当前没有需要人工介入的运行。</p>"
    )
    body = f"""
    <h1>Pipeliner MVP</h1>
    <p>这是从 canonical <code>workflow spec</code> 与 runtime 状态派生出的最小 operator 视图。</p>
    <h2>需要人工介入的 Runs</h2>
    {table}
    <p>API: <a href=\"/docs\">/docs</a></p>
    """
    return _page("Pipeliner MVP", body)


def render_workflow_view(workflow: dict[str, Any]) -> str:
    nodes = workflow["spec"]["nodes"]
    rows = [
        [
            node["node_id"],
            node["title"],
            ", ".join(node["depends_on"]),
            node["executor"]["skill"],
        ]
        for node in nodes
    ]
    body = f"""
    <h1>{escape(workflow['workflow_id'])}@{escape(workflow['version'])}</h1>
    <p>{escape(workflow['title'])}</p>
    <p>此页面仅为从 <code>workflow spec</code> 派生的只读视图，机器真源仍是注册的 spec JSON。</p>
    <h2>Nodes</h2>
    {_table(["Node", "Title", "Depends On", "Executor Skill"], rows)}
    <h2>Lint Warnings</h2>
    <pre>{escape(workflow['warnings'])}</pre>
    """
    return _page(f"Workflow {workflow['workflow_id']}", body)


def render_run_view(detail: dict[str, Any], callbacks: list[dict[str, Any]]) -> str:
    run = detail["run"]
    nodes = detail["nodes"]
    artifacts = detail["artifacts"]
    node_rows = [
        [
            node["node_id"],
            node["round_no"],
            node["status"],
            node.get("waiting_for_role", ""),
            node.get("stop_reason", ""),
        ]
        for node in nodes
    ]
    artifact_rows = [
        [artifact["artifact_id"], artifact["version"], artifact["kind"], artifact["storage_uri"]]
        for artifact in artifacts
    ]
    callback_rows = [
        [
            item["event_id"],
            item["node_id"],
            item["round_no"],
            item["actor_role"],
            item.get("verdict_status", ""),
        ]
        for item in callbacks
    ]
    workflow_label = (
        f"{detail['workflow']['workflow_id']}@{detail['workflow']['version']}"
    )
    status_class = "attention" if run["status"] == "needs_attention" else ""
    artifact_section = (
        _table(["Artifact", "Version", "Kind", "Storage URI"], artifact_rows)
        if artifact_rows
        else "<p>暂无 artifact。</p>"
    )
    callback_section = (
        _table(["Event", "Node", "Round", "Actor", "Verdict"], callback_rows)
        if callback_rows
        else "<p>暂无 callback。</p>"
    )
    body = f"""
    <h1>Run {escape(run['id'])}</h1>
    <p>
      <span class=\"badge {status_class}\">{escape(run['status'])}</span>
      Workflow: <code>{escape(workflow_label)}</code>
    </p>
    <p>Workspace: <code>{escape(run['workspace_root'])}</code></p>
    <h2>Nodes</h2>
    {_table(["Node", "Round", "Status", "Waiting For", "Stop Reason"], node_rows)}
    <h2>Artifacts</h2>
    {artifact_section}
    <h2>Callbacks</h2>
    {callback_section}
    """
    return _page(f"Run {run['id']}", body)
