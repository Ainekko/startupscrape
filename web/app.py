"""
app.py — FlowJoy Lead Browse Page

Routes:
  GET  /          — list all runs, show latest by default
  GET  /runs/<id> — browse a specific run
  POST /run       — trigger a new pipeline run (background thread)
  GET  /status    — current active run status
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

# track active run
_run_lock = threading.Lock()
_active_run: dict[str, Any] | None = None


# ─── helpers ─────────────────────────────────────────────────────────────────

def _list_runs() -> list[dict]:
    runs = []
    for p in sorted(DATA_DIR.glob("run_*.json"), reverse=True):
        if "_partial" in p.name:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            runs.append({
                "run_id": data.get("run_id", p.stem),
                "started_at": data.get("started_at", ""),
                "status": data.get("status", "complete"),
                "funnel": data.get("funnel", {}),
                "spend": data.get("spend", {}),
                "lead_count": len(data.get("leads", [])),
                "path": str(p),
            })
        except Exception:
            pass
    return runs


def _load_run(run_id: str) -> dict | None:
    candidates = list(DATA_DIR.glob(f"{run_id}*.json"))
    if not candidates:
        return None
    path = sorted(candidates)[-1]
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _trigger_run() -> None:
    global _active_run
    try:
        from pipeline.runner import run as pipeline_run
        result = pipeline_run(max_leads=20, max_treg_cost=1.0)
        with _run_lock:
            _active_run = {"status": "done", "run_id": result["run_id"]}
    except Exception as e:
        logger.error("Pipeline run failed: %s", e)
        with _run_lock:
            _active_run = {"status": "error", "error": str(e)}


# ─── routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    runs = _list_runs()
    latest = runs[0] if runs else None
    run_data = None
    if latest:
        run_data = _load_run(latest["run_id"])
    with _run_lock:
        active = _active_run
    return render_template("index.html", runs=runs, run=run_data, active_run=active)


@app.route("/runs/<run_id>")
def view_run(run_id: str):
    runs = _list_runs()
    run_data = _load_run(run_id)
    if not run_data:
        return "Run not found", 404
    with _run_lock:
        active = _active_run
    return render_template("index.html", runs=runs, run=run_data, active_run=active)


@app.route("/run", methods=["POST"])
def trigger_run():
    global _active_run
    with _run_lock:
        if _active_run and _active_run.get("status") == "running":
            return jsonify({"error": "A run is already in progress"}), 409
        _active_run = {"status": "running"}
    t = threading.Thread(target=_trigger_run, daemon=True)
    t.start()
    return redirect(url_for("index"))


@app.route("/status")
def run_status():
    with _run_lock:
        return jsonify(_active_run or {"status": "idle"})


@app.route("/api/runs")
def api_runs():
    return jsonify(_list_runs())


@app.route("/api/runs/<run_id>")
def api_run(run_id: str):
    data = _load_run(run_id)
    if not data:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, port=port, use_reloader=False)
