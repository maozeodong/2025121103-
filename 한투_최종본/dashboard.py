"""Tiny browser dashboard for the KIS final project.

Run:
    python3 dashboard.py

Open:
    http://localhost:8000
"""

from __future__ import annotations

import html
import json
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATUS_PATH = ROOT / "logs" / "status.json"
LOG_PATH = ROOT / "logs" / "trader.log"


def read_status() -> dict:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": "status.json is not valid JSON"}


def read_log() -> str:
    if not LOG_PATH.exists():
        return "No log yet. Run kis_live_once_stdlib.py first."
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-80:])


def money(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "-"


def pct(value) -> str:
    try:
        return f"{float(value) * 100:.4f}%"
    except (TypeError, ValueError):
        return "-"


def render_page() -> bytes:
    status = read_status()
    log = read_log()
    cards = [
        ("Timestamp", status.get("timestamp", "-")),
        ("Symbol", status.get("symbol", "-")),
        ("Dry Run", str(status.get("dry_run", "-"))),
        ("Current Price", money(status.get("current_price"))),
        ("Quantity", money(status.get("quantity"))),
        ("Cash", money(status.get("cash"))),
        ("Average Price", money(status.get("average_price"))),
        ("Action", status.get("action", "-")),
        ("Buy Limit", money(status.get("buy_price"))),
        ("Sell Limit", money(status.get("sell_price"))),
        ("Expected Return", pct(status.get("expected_return"))),
        ("Loss Probability", pct(status.get("loss_probability"))),
    ]
    card_html = "\n".join(
        f'<section class="card"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(str(value))}</div></section>'
        for label, value in cards
    )
    reason = html.escape(str(status.get("reason", "Run kis_live_once_stdlib.py first.")))
    order = html.escape(json.dumps(status.get("order", {}), ensure_ascii=False, indent=2))
    log_html = html.escape(log)
    body = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="5">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KIS Finance Dashboard</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #15171a; }}
    header {{ padding: 22px 28px; background: #101820; color: white; }}
    h1 {{ margin: 0; font-size: 22px; }}
    main {{ padding: 24px 28px; max-width: 1180px; margin: 0 auto; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 14px; }}
    .label {{ font-size: 12px; color: #667085; margin-bottom: 8px; }}
    .value {{ font-size: 20px; font-weight: 700; overflow-wrap: anywhere; }}
    .panel {{ margin-top: 18px; background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 16px; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #0f172a; color: #e5e7eb; padding: 14px; border-radius: 6px; max-height: 360px; overflow: auto; }}
    .reason {{ font-size: 16px; line-height: 1.5; }}
  </style>
</head>
<body>
  <header><h1>KIS Finance Dashboard</h1></header>
  <main>
    <div class="grid">{card_html}</div>
    <section class="panel"><h2>Strategy Reason</h2><div class="reason">{reason}</div></section>
    <section class="panel"><h2>Order Response</h2><pre>{order}</pre></section>
    <section class="panel"><h2>Recent Log</h2><pre>{log_html}</pre></section>
  </main>
</body>
</html>"""
    return body.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        body = render_page()
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local KIS dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Dashboard: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
