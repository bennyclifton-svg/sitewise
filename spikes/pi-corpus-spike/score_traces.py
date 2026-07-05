"""Score pi corpus spike JSON traces into a summary table."""
from __future__ import annotations

import json
from pathlib import Path

ESCAPE_TOOLS = {
    "bash",
    "read",
    "write",
    "edit",
    "grep",
    "find",
    "ls",
}
RETRIEVAL = {
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
NON_RETRIEVAL_CLERK = {
    "clerk_write_workspace_file",
    "clerk_read_workspace_file",
    "clerk_list_workspace",
    "clerk_list_tender_comparisons",
    "clerk_get_tender_comparison",
    "clerk_get_comparison_status",
    "clerk_get_comparison_result",
    "clerk_start_tender_comparison",
    "clerk_list_selected_documents",
}


def parse_trace(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    if "Unknown option" in text or text.strip().startswith("node.exe"):
        return {"error": "pi_failed", "tools": [], "dispatched": [], "answer": ""}

    tools: list[str] = []
    dispatched: list[str] = []
    answer_parts: list[str] = []

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
            if name == "mcp" and args.get("tool"):
                tool = str(args["tool"])
                if tool not in dispatched:
                    dispatched.append(tool)
        elif etype == "message_end":
            msg = evt.get("message") or {}
            if msg.get("role") == "assistant":
                for part in msg.get("content") or []:
                    if part.get("type") == "text" and part.get("text"):
                        answer_parts.append(part["text"])

    ordered = dispatched or [t for t in tools if t != "mcp"] or tools
    escape = any(t in ESCAPE_TOOLS for t in tools)
    escape = escape or any(t in NON_RETRIEVAL_CLERK for t in dispatched)
    return {
        "tools": tools,
        "dispatched": dispatched,
        "ordered": ordered,
        "escape": escape,
        "answer": "\n".join(answer_parts).strip(),
    }


def main() -> None:
    results_dir = Path(__file__).parent / "results"
    print("| # | Condition | Tools called (in order) | Escape? | Answer excerpt |")
    print("| --- | --- | --- | --- | --- |")
    for cond in ("locked", "open"):
        for i in range(1, 9):
            path = results_dir / f"{cond}-q{i}.json"
            if not path.exists():
                print(f"| {i} | {cond} | MISSING | | | |")
                continue
            p = parse_trace(path)
            tools = " → ".join(p["ordered"]) if p["ordered"] else "(none)"
            excerpt = (p.get("answer") or p.get("error", "")).replace("|", "/").replace("\n", " ")[:100]
            print(f"| {i} | {cond} | {tools} | {p['escape']} | {excerpt} |")


if __name__ == "__main__":
    main()
