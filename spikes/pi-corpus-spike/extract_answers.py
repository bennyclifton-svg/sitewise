"""Extract final assistant answers and tool chains from pi JSON traces."""
from __future__ import annotations

import json
from pathlib import Path

NON_RETRIEVAL = {
    "bash", "read", "write", "edit", "grep", "find", "ls",
    "clerk_write_workspace_file", "clerk_read_workspace_file", "clerk_list_workspace",
    "clerk_list_tender_comparisons", "clerk_start_tender_comparison",
}


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    tools: list[str] = []
    dispatched: list[str] = []
    answers: list[str] = []

    for line in text.splitlines():
        if not line.strip().startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = evt.get("type")
        if t == "tool_execution_start":
            n = evt.get("toolName", "")
            if n and n not in tools:
                tools.append(n)
            args = evt.get("args") or {}
            if n == "mcp" and args.get("tool"):
                tool = str(args["tool"])
                if tool not in dispatched:
                    dispatched.append(tool)
        elif t == "message_end":
            msg = evt.get("message") or {}
            if msg.get("role") == "assistant":
                for part in msg.get("content") or []:
                    if part.get("type") == "text" and part.get("text"):
                        answers.append(part["text"])

    chain = dispatched or [x for x in tools if x != "mcp"]
    escape = any(x in NON_RETRIEVAL for x in tools + dispatched)
    return {
        "chain": chain,
        "escape": escape,
        "answer": answers[-1] if answers else "",
    }


def main() -> None:
    base = Path(__file__).parent / "results"
    for cond in ("locked", "open"):
        print(f"\n=== {cond.upper()} ===")
        for i in range(1, 9):
            p = base / f"{cond}-q{i}.json"
            if not p.exists():
                print(f"Q{i}: MISSING")
                continue
            r = parse(p)
            chain = " -> ".join(r["chain"]) or "(none)"
            ans = r["answer"].replace("\n", " ")[:200]
            print(f"Q{i} [{chain}] escape={r['escape']}")
            print(f"   {ans}")


if __name__ == "__main__":
    main()
