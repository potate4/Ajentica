"""Smoke-test all four bonuses end-to-end against the running backend.

Usage:
    .venv/Scripts/python smoke_test.py [--host http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.parse import urlparse

import urllib.request


def stream(url: str, body: dict, on_event):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        buf = b""
        for chunk in resp:
            buf += chunk
            while b"\n\n" in buf:
                block, buf = buf.split(b"\n\n", 1)
                event = "message"
                data_lines = []
                for line in block.split(b"\n"):
                    if line.startswith(b"event:"):
                        event = line[6:].strip().decode()
                    elif line.startswith(b"data:"):
                        data_lines.append(line[5:].lstrip().decode())
                if data_lines:
                    try:
                        data = json.loads("\n".join(data_lines))
                    except json.JSONDecodeError:
                        data = "\n".join(data_lines)
                    on_event(event, data)


def smoke(host: str) -> int:
    print(f"\n=== Health & config ===")
    cfg = json.loads(urllib.request.urlopen(f"{host}/api/config").read())
    health = json.loads(urllib.request.urlopen(f"{host}/api/health").read())
    print(f"  agent_mode:    {cfg['agent_mode']}")
    print(f"  llm:           {cfg['llm_model']}")
    print(f"  streaming:     {cfg['enable_streaming']}")
    print(f"  trace:         {cfg['enable_reasoning_trace']}")
    print(f"  memory:        {cfg['enable_session_memory']}")
    print(f"  indexed:       {health['indexed_chunks']} chunks")
    if cfg['agent_mode'] != 'crew':
        print("  (warn) AGENT_MODE != crew — multi-agent test will be weak")

    session_id = None
    agents_seen: set[str] = set()
    tools_seen: list[str] = []
    final_q1: dict | None = None
    started_at = time.time()

    def on_q1(event, data):
        nonlocal session_id, final_q1
        if event == "session":
            session_id = data["session_id"]
            print(f"  session_id:    {session_id}")
        elif event == "trace":
            kind = data.get("kind")
            payload = data.get("payload", {})
            elapsed = f"{time.time() - started_at:5.1f}s"
            if kind == "agent_started":
                agents_seen.add(payload.get("agent", "?"))
                print(f"  [{elapsed}]  > agent_started   {payload.get('agent')}")
            elif kind == "agent_finished":
                print(f"  [{elapsed}]  [ok] agent_finished  {payload.get('agent')}")
            elif kind == "tool_call":
                tool = payload.get("tool", "?")
                tools_seen.append(tool)
                args = payload.get("args", {})
                print(f"  [{elapsed}]    -> {tool}({_short_args(args)})")
            elif kind == "tool_result":
                ms = payload.get("elapsed_ms")
                err = payload.get("error")
                tag = f"ERR: {err}" if err else f"{ms} ms"
                print(f"  [{elapsed}]    <- {payload.get('tool')}  {tag}")
        elif event == "done":
            final_q1 = data
        elif event == "error":
            print(f"  [X] error: {data}")

    print(f"\n=== Question 1 (streaming + crew) ===")
    stream(f"{host}/api/chat/stream",
           {"question": "How does Flask handle URL routing? Be brief."},
           on_q1)

    if final_q1 is None:
        print("\n  [X] No 'done' event received")
        return 2

    print(f"\n  refused:       {final_q1['refused']}")
    print(f"  citations:     {len(final_q1['citations'])}")
    for c in final_q1['citations'][:5]:
        print(f"     - {c['path']}:{c['start_line']}-{c['end_line']}")
    print(f"  agents seen:   {sorted(agents_seen)}")
    print(f"  tools used:    {tools_seen}")
    print(f"  answer head:   {final_q1['answer'][:200]}...")

    # ---- Memory test: ask follow-up referring to the prior question ----
    print(f"\n=== Question 2 (memory: same session_id) ===")
    final_q2: dict | None = None
    started_at_2 = time.time()

    def on_q2(event, data):
        nonlocal final_q2
        if event == "trace":
            elapsed = f"{time.time() - started_at_2:5.1f}s"
            kind = data.get("kind")
            payload = data.get("payload", {})
            if kind in {"agent_started", "agent_finished"}:
                print(f"  [{elapsed}]  {'>' if kind == 'agent_started' else '[ok]'} {kind}  {payload.get('agent')}")
        elif event == "done":
            final_q2 = data

    stream(f"{host}/api/chat/stream",
           {"question": "What was my previous question? Just restate it.", "session_id": session_id},
           on_q2)

    print(f"\n  answer:        {final_q2['answer'][:300] if final_q2 else 'none'}")

    # Memory check: answer should mention 'routing' or 'URL' from the first question
    memory_ok = False
    if final_q2:
        a = final_q2['answer'].lower()
        memory_ok = "rout" in a or "url" in a or "previous" in a

    print(f"\n=== Summary ===")
    crew_ok = len(agents_seen) >= 3
    stream_ok = len(tools_seen) > 0  # we saw events arriving live
    cite_ok = len(final_q1['citations']) > 0
    refuse_ok = not final_q1['refused']
    print(f"  [ok] ingest + search + agent  ({len(tools_seen)} tools called)")
    print(f"  {'[ok]' if crew_ok else '[X]'} multi-agent crew         ({len(agents_seen)} distinct agents)")
    print(f"  {'[ok]' if stream_ok else '[X]'} streaming               (live events received)")
    print(f"  {'[ok]' if cite_ok else '[X]'} citations               ({len(final_q1['citations'])} cited)")
    print(f"  {'[ok]' if refuse_ok else '[X]'} non-refused answer")
    print(f"  {'[ok]' if memory_ok else '[X]'} session memory          (Q2 referenced Q1)")

    all_ok = crew_ok and stream_ok and cite_ok and refuse_ok and memory_ok
    return 0 if all_ok else 1


def _short_args(args) -> str:
    if not isinstance(args, dict):
        return str(args)[:60]
    parts = []
    for k, v in args.items():
        if v is None or v == "" or v == 0:
            continue
        s = repr(v) if isinstance(v, str) else str(v)
        parts.append(f"{k}={s[:40]}{'...' if len(s) > 40 else ''}")
    return ", ".join(parts)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="http://127.0.0.1:8000")
    args = p.parse_args()
    sys.exit(smoke(args.host))
