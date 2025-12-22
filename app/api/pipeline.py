### FICHIER MIGRÉ. Voir app/api/pipeline.py

from fastapi import APIRouter
from starlette.responses import StreamingResponse
from typing import Dict
import threading
import sys
from pathlib import Path
import time
from collections import deque

router = APIRouter()

pipeline_status = {
    "percent": 0,
    "step": "En attente",
    "running": False
}


# Buffer circulaire pour logs pipeline (thread-safe)
PIPELINE_LOG_MAX_LINES = 500
pipeline_logs = deque(maxlen=PIPELINE_LOG_MAX_LINES)
pipeline_logs_lock = threading.Lock()
pipeline_process = {"proc": None}

def set_pipeline_status(percent, step):
    pipeline_status["percent"] = percent
    pipeline_status["step"] = step
    pipeline_status["running"] = percent < 100

@router.get("/pipeline-status")
def get_pipeline_status():
    return pipeline_status

def append_pipeline_log(line):
    with pipeline_logs_lock:
        pipeline_logs.append(line.rstrip())

@router.get("/pipeline-logs")
def stream_pipeline_logs():
    """
    Stream les logs du pipeline en temps réel (texte brut, type text/event-stream ou text/plain).
    """
    def event_stream():
        last_idx = 0
        while True:
            with pipeline_logs_lock:
                logs = list(pipeline_logs)
            # Envoie les nouvelles lignes
            for line in logs[last_idx:]:
                yield line + "\n"
            last_idx = len(logs)
            time.sleep(0.5)
            # Arrêt si pipeline terminé et plus de nouvelles lignes
            if not pipeline_status["running"] and last_idx >= len(logs):
                break
    return StreamingResponse(event_stream(), media_type="text/plain")

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
        # Stocke le PID dans un fichier temporaire
        pid_file = Path("/tmp/pipeline.pid")
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        try:
            step_map = {
                "fetch_raw_messages_24h": (20, "Fetching"),
                "translate_messages": (50, "Translation"),
                "enrich_messages": (70, "Enrichment"),
                "dedupe_messages": (80, "Deduplication"),
                "store_messages": (90, "Storing"),
                "delete_old_messages": (95, "Cleaning"),
                "Pipeline terminé": (100, "Done!")
            }
            current_percent = 0
            current_step = "Initialisation"
            for line in proc.stdout:
                line = line.rstrip("\n")
                append_pipeline_log(line)
                for key, (percent, step) in step_map.items():
                    if key in line:
                        set_pipeline_status(percent, step)
                        current_percent = percent
                        current_step = step
                        break
                if pipeline_process["proc"] is None:
                    set_pipeline_status(100, "Cancelled")
                    proc.terminate()
                    return
            proc.wait()
            set_pipeline_status(100, "Done!")
        finally:
            pipeline_process["proc"] = None
            # Supprime le fichier PID
            try:
                pid_file.unlink()
            except Exception:
                pass

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return {"status": "started"}

@router.post("/stop-pipeline")
def stop_pipeline():
    import os
    from pathlib import Path
    proc = pipeline_process.get("proc")
    pid_file = Path("/tmp/pipeline.pid")
    killed = False
    if proc and proc.poll() is None:
        proc.terminate()
        pipeline_process["proc"] = None
        set_pipeline_status(100, "Cancelled")
        killed = True
    elif pid_file.exists():
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)  # SIGTERM
            set_pipeline_status(100, "Cancelled")
            killed = True
            pid_file.unlink()
        except Exception as e:
            return {"status": "error", "detail": str(e)}
    if killed:
        return {"status": "stopped"}
    return {"status": "no-process"}
