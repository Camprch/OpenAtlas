from fastapi import APIRouter
from starlette.responses import StreamingResponse
from typing import Dict
import threading
import sys
from pathlib import Path
import time
from collections import deque

# Router for pipeline control/status endpoints
router = APIRouter()

# Shared status state for the UI
pipeline_status = {
    "percent": 0,
    "step": "En attente",
    "running": False
}


# Thread-safe circular buffer for pipeline logs
PIPELINE_LOG_MAX_LINES = 500
pipeline_logs = deque(maxlen=PIPELINE_LOG_MAX_LINES)
pipeline_logs_lock = threading.Lock()
pipeline_process = {"proc": None}

def set_pipeline_status(percent, step):
    # Update status and infer running state from progress
    pipeline_status["percent"] = percent
    pipeline_status["step"] = step
    pipeline_status["running"] = percent < 100

@router.get("/pipeline-status")
def get_pipeline_status():
    # Expose current pipeline status
    return pipeline_status

def append_pipeline_log(line):
    # Append a single log line to the shared buffer
    with pipeline_logs_lock:
        pipeline_logs.append(line.rstrip())

@router.get("/pipeline-logs")
def stream_pipeline_logs():
    """
    Stream pipeline logs in real time (plain text).
    """
    def event_stream():
        last_idx = 0
        while True:
            with pipeline_logs_lock:
                logs = list(pipeline_logs)
            # Send only new lines since the last iteration
            for line in logs[last_idx:]:
                yield line + "\n"
            last_idx = len(logs)
            time.sleep(0.5)
            # Stop when finished and there are no new lines
            if not pipeline_status["running"] and last_idx >= len(logs):
                break
    return StreamingResponse(event_stream(), media_type="text/plain")

@router.post("/run-pipeline")
def run_pipeline_real():
    """
    Run the Python pipeline (tools/run_pipeline.py) in a thread and update status in real time.
    """
    def target():
        import subprocess
        import os
        import sys
        from pathlib import Path
        import time

        # Reset status before launching the subprocess
        set_pipeline_status(0, "Initialisation")
        project_root = Path(__file__).resolve().parent.parent.parent
        script_path = project_root / "tools" / "run_pipeline.py"

        # Launch the pipeline and stream stdout for progress updates
        proc = subprocess.Popen([
            sys.executable,
            str(script_path)
        ], cwd=str(project_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        pipeline_process["proc"] = proc
        # Store PID so other endpoints can stop the process
        pid_file = Path("/tmp/pipeline.pid")
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        try:
            # Map log markers to progress/status labels
            step_map = {
                "init_db()": (5, "Init"),
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
                if "[ABORTED]" in line:
                    set_pipeline_status(100, f"Aborted: {line.split('[ABORTED]', 1)[-1].strip()}")
                    proc.terminate()
                    return
                for key, (percent, step) in step_map.items():
                    if key in line:
                        set_pipeline_status(percent, step)
                        current_percent = percent
                        current_step = step
                        break
                # Allow external stop to cancel the subprocess
                if pipeline_process["proc"] is None:
                    set_pipeline_status(100, "Cancelled")
                    proc.terminate()
                    return
            proc.wait()
            set_pipeline_status(100, "Done!")
        finally:
            pipeline_process["proc"] = None
            # Clean up the PID file if it exists
            try:
                pid_file.unlink()
            except Exception:
                pass

    # Run in background so the API call returns immediately
    t = threading.Thread(target=target, daemon=True)
    t.start()
    return {"status": "started"}

@router.post("/stop-pipeline")
def stop_pipeline():
    import os
    from pathlib import Path
    # Attempt to stop the running pipeline, if any
    proc = pipeline_process.get("proc")
    pid_file = Path("/tmp/pipeline.pid")
    killed = False
    if proc and proc.poll() is None:
        # Stop the tracked subprocess first
        proc.terminate()
        pipeline_process["proc"] = None
        set_pipeline_status(100, "Cancelled")
        killed = True
    elif pid_file.exists():
        # Fallback to PID file in case the process was orphaned
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
