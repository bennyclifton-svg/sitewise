"""Score pi corpus spike JSON traces into a summary table."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ESCAPE_TOOLS = {
    "bash",
    "read",
    "write",
    "edit",
    "grep",
    "find",
    "ls",
    "clerk_write_workspace_file",
    "clerk_read_workspace_file",
    "clerk_list_workspace",
}
RETRIEVAL_TOOLS = {
    "find_document_text",
    "search_documents",
    "get_document",
    "list_platform_knowledge",
    "read_platform_knowledge",
    "clerk_find_document_text",
    "clerk_search_documents",
    "clerk_get_document",
    "clerk_list_platform_knowledge",
    "clerk_read_platform_knowledge",
}


def parse_trace(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    if text.strip().startswith("node.exe") or "Unknown option" in text:
        return {"error": "pi_failed", "tools": [], "answer": ""}

    tools: list[str] = []
    answer_parts: list[str] = []
    mcp_modes: list[str] = []
    mcp_dispatched: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = evt.get("type")
        if etype == "tool_execution_start":
            name = evt.get("toolName", "")
            if name and name not in tools:
                tools.append(name)
            args = evt.get("args") or {}
            if name == "mcp":
                if args.get("tool"):
                    mcp_dispatched.append(str(args["tool"]))
                elif args.get("search"):
                    mcp_modes.append("search")
        elif etype == "tool_execution_end":
            details = (evt.get("result") or {}).get("details") or {}
            if evt.get("toolName") == "mcp" and details.get("mode") == "search":
                mcp_modes.append("search")
        elif etype == "message_end":
            msg = evt.get("message") or {}
            if msg.get("role") == "assistant":
                for part in msg.get("content") or []:
                    if part.get("type") == "text" and part.get("text"):
                        answer_parts.append(part["text"])

    for t in mcp_dispatched:
        if t not in tools:
            tools.append(t)

    escape = any(
        t in ESCAPE_TOOLS or t.replace("clerk_", "") in {"write_workspace_file", "read_workspace_file", "list_workspace"}
        for t in tools + mcp_dispatched
    )
    if "search" in mcp_modes and any(
        m in str((json.loads(line)["tool_execution_end"] if False else "")) for line in []
    ):
        pass

    # Escape if mcp search discovered non-retrieval tools and agent used workspace/tender tools
    non_retrieval_mcp = [
        t
        for t in mcp_dispatched
        if t not in RETRIEVAL_TOOLS and t.startswith("clerk_")
    ]
    if non_retrieval_mcp:
        escape = True

    answer = "\n".join(answer_parts).strip()
    return {
        "tools": tools,
        "mcp_dispatched": mcp_dispatched,
        "mcp_modes": mcp_modes,
        "escape": escape,
        "answer": answer[:500],
    }


def main() -> None:
    results_dir = Path(__file__).parent / "results"
    conditions = ["locked", "open"]
    rows = []
    for cond in conditions:
        for i in range(1, 9):
            path = results_dir / f"{cond}-q{i}.json"
            if not path.exists():
                rows.append((i, cond, "MISSING", False, False, "trace missing"))
                continue
            parsed = parse_trace(path)
            tool_str = " -> ".join(
                parsed.get("mcp_dispatched") or parsed.get("tools") or ["(none)"]
            )
            rows.append(
                (
                    i,
                    cond,
                    tool_str,
                    parsed.get("escape", False),
                    bool(parsed.get("answer")),
                    parsed.get("answer", "")[:120] or parsed.get("error", ""),
                )
            )

    print("| # | Condition | Tools called | Escape? | Has answer? | Notes |")
    print("| --- | --- | --- | --- | --- | --- |")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")


if __name__ == "__main__":
    main()
