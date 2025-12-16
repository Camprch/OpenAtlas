from fastapi import APIRouter
from starlette.responses import StreamingResponse
from typing import Dict
import threading
import sys
from pathlib import Path

router = APIRouter()

pipeline_status = {
    "percent": 0,
    "step": "En attente",
    "running": False
}

pipeline_process = {"proc": None}

def set_pipeline_status(percent, step):
    pipeline_status["percent"] = percent
    pipeline_status["step"] = step
    pipeline_status["running"] = percent < 100

@router.get("/pipeline-status")
def get_pipeline_status():
    return pipeline_status

@router.post("/run-pipeline")
def run_pipeline_real():
    """
    Lance réellement le pipeline Python (tools/run_pipeline.py) dans un thread et met à jour le statut en temps réel.
    """
    def target():
        import subprocess
        import os
        import sys
        from pathlib import Path
        import time

        set_pipeline_status(0, "Initialisation")
        project_root = Path(__file__).resolve().parent.parent.parent
        script_path = project_root / "tools" / "run_pipeline.py"

        proc = subprocess.Popen([
            sys.executable,
            str(script_path)
        ], cwd=str(project_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        pipeline_process["proc"] = proc
        try:
            step_map = {
                "fetch_raw_messages_24h": (20, "Collecte"),
                "translate_messages": (50, "Traduction"),
                "enrich_messages": (70, "Enrichissement"),
                "dedupe_messages": (80, "Traitement"),
                "store_messages": (90, "Stockage"),
                "delete_old_messages": (95, "Nettoyage"),
                "Pipeline terminé": (100, "Terminé")
            }
            current_percent = 0
            current_step = "Initialisation"
            for line in proc.stdout:
                line = line.strip()
                for key, (percent, step) in step_map.items():
                    if key in line:
                        set_pipeline_status(percent, step)
                        current_percent = percent
                        current_step = step
                        break
                if pipeline_process["proc"] is None:
                    set_pipeline_status(100, "Annulé")
                    proc.terminate()
                    return
            proc.wait()
            set_pipeline_status(100, "Terminé")
        finally:
            pipeline_process["proc"] = None

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return {"status": "started"}

@router.post("/stop-pipeline")
def stop_pipeline():
    proc = pipeline_process.get("proc")
    if proc and proc.poll() is None:
        proc.terminate()
        pipeline_process["proc"] = None
        set_pipeline_status(100, "Annulé")
        return {"status": "stopped"}
    return {"status": "no-process"}
