#!/usr/bin/env python3
"""
scripts/demo.py — End-to-end demo of the AI Office platform.
Submits a sample request and polls until completion, printing live events.
"""
import sys
import time
import json
import httpx

API = "http://localhost:8000"

DEMO_REQUEST = (
    "Research the market for AI coding assistants (size, top 5 competitors, pricing), "
    "design a microservice architecture for a new AI coding assistant SaaS product, "
    "and build a minimal Python health-check endpoint with tests."
)

GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def p(color, label, msg):
    print(f"{color}[{label}]{RESET} {msg}")


def main():
    print(f"\n{BOLD}🏢  AI Office — End-to-End Demo{RESET}")
    print("─" * 52)

    # 1. Health check
    try:
        r = httpx.get(f"{API}/health", timeout=5)
        r.raise_for_status()
        p(GREEN, "health", f"API online — {r.json()}")
    except Exception as e:
        p(RED, "error", f"API not reachable at {API}: {e}")
        p(RED, "hint", "Run: docker compose up -d")
        sys.exit(1)

    # 2. Start conversation
    p(CYAN, "request", DEMO_REQUEST[:80] + "...")
    r = httpx.post(f"{API}/api/v1/conversations", json={"request": DEMO_REQUEST}, timeout=30)
    r.raise_for_status()
    conv_id = r.json()["conversation_id"]
    trace_id = r.json()["trace_id"]
    p(GREEN, "started", f"conversation_id={conv_id[:12]}... trace_id={trace_id[:12]}...")

    # 3. Poll for completion
    print(f"\n{DIM}{'─'*52}{RESET}")
    seen_events = 0
    for attempt in range(120):  # max 4 minutes
        time.sleep(2)
        r = httpx.get(f"{API}/api/v1/conversations/{conv_id}", timeout=10)
        r.raise_for_status()
        conv = r.json()

        # Print new events
        events = conv.get("events", [])
        for ev in events[seen_events:]:
            t = ev["timestamp"][11:19]
            etype = ev["type"]
            data_str = json.dumps(ev.get("data", {}))[:80]
            color = GREEN if "completed" in etype else CYAN if "started" in etype else YELLOW
            p(color, f"{t} {etype}", data_str)
        seen_events = len(events)

        status = conv.get("status")
        if status == "completed":
            break
        elif status == "failed":
            p(RED, "failed", conv.get("error", "Unknown error"))
            sys.exit(1)

    # 4. Print deliverable
    r = httpx.get(f"{API}/api/v1/conversations/{conv_id}/deliverable", timeout=10)
    if r.status_code == 200:
        d = r.json()
        print(f"\n{BOLD}{'─'*52}")
        print(f"📦  Deliverable{RESET}")
        print(f"  Summary      : {d.get('summary')}")
        print(f"  Tasks        : {d.get('success_count')}/{d.get('task_count')} succeeded")
        print(f"  Avg Confidence: {d.get('avg_confidence', 0):.1%}")
        if d.get("requires_human_review"):
            p(YELLOW, "review", f"Human review needed: {d['requires_human_review']}")
    
    # 5. Print agent stats
    r = httpx.get(f"{API}/api/v1/agents", timeout=10)
    if r.status_code == 200:
        print(f"\n{BOLD}🤖  Agent Stats{RESET}")
        for a in r.json():
            rel = a["reliability_score"] * 100
            p(CYAN, a["agent_id"].replace("_agent",""), 
              f"reliability={rel:.0f}%  tasks={a['total_tasks']}  "
              f"confidence={a['avg_confidence']:.1%}  latency={a['avg_latency_ms']:.0f}ms")

    print(f"\n{GREEN}{'─'*52}")
    print(f"✅  Demo complete!  Dashboard → http://localhost:3000{RESET}\n")


if __name__ == "__main__":
    main()
