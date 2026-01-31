// --- PIPELINE LOG STREAMING ---
let pipelineLogController = null;
let pipelineLogReader = null;
let pipelineLogActive = false;

export function showPipelineLogs() {
    // Show the log container in the UI
    const container = document.getElementById('pipeline-logs-container');
    if (container) container.style.display = 'block';
}

export function hidePipelineLogs() {
    // Hide the log container and clear its contents
    const container = document.getElementById('pipeline-logs-container');
    if (container) container.style.display = 'none';
    const logs = document.getElementById('pipeline-logs');
    if (logs) logs.textContent = '';
}

export async function streamPipelineLogs() {
    // Stream server-side logs via a streaming response
    showPipelineLogs();
    const logs = document.getElementById('pipeline-logs');
    if (!logs) return;
    pipelineLogActive = true;
    pipelineLogController = new AbortController();
    try {
        const resp = await fetch('/api/pipeline-logs', { signal: pipelineLogController.signal });
        if (!resp.body) return;
        const reader = resp.body.getReader();
        pipelineLogReader = reader;
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        while (pipelineLogActive) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            // Split and append completed lines
            let lines = buffer.split('\n');
            buffer = lines.pop(); // la dernière ligne peut être incomplète
            for (const line of lines) {
                logs.textContent += line + '\n';
            }
            logs.scrollTop = logs.scrollHeight;
        }
        if (buffer) {
            logs.textContent += buffer + '\n';
            logs.scrollTop = logs.scrollHeight;
        }
    } catch (e) {
        // ignore si abort
    }
}

export function stopPipelineLogs() {
    // Stop streaming and clean up readers/controllers
    pipelineLogActive = false;
    if (pipelineLogController) pipelineLogController.abort();
    pipelineLogController = null;
    pipelineLogReader = null;
    hidePipelineLogs();
}

export async function resumePipelineIfRunning(pipelineBarBtn, pipelineBarFill, pipelineBarLabel, startPipelineCb, stopPipelineCb) {
    // Restore pipeline UI state if a run is already in progress
    const pipelinePercent = document.getElementById('pipeline-percent');
    const resp = await fetch('/api/pipeline-status');
    const data = await resp.json();
    if (data.running) {
        pipelineBarBtn.disabled = false;
        pipelineBarBtn.style.cursor = 'pointer';
        pipelineBarBtn.style.background = '#23272f';
        pipelineBarBtn.classList.add('pipeline-running');
        pipelineBarLabel.textContent = data.step || 'Cancel';
        pipelineBarFill.style.width = data.percent + '%';
        if (pipelinePercent) {
            pipelinePercent.textContent = `${data.percent}%`;
            pipelinePercent.style.display = 'inline';
        }
        pipelineBarBtn.onclick = stopPipelineCb;
        pipelineRunning = true;
        // Poll for status updates while running
        pipelinePolling = setInterval(async () => {
            const statusResp = await fetch('/api/pipeline-status');
            if (statusResp.ok) {
                const d = await statusResp.json();
                pipelineBarFill.style.width = d.percent + '%';
                pipelineBarLabel.textContent = `${d.step || ''}`;
                if (pipelinePercent) pipelinePercent.textContent = `${d.percent}%`;
                if (d.percent >= 100 || d.step === 'Cancelled') {
                    clearInterval(pipelinePolling);
                    pipelineBarBtn.onclick = null;
                    pipelineBarBtn.style.cursor = 'default';
                    pipelineBarBtn.disabled = true;
                    pipelineRunning = false;
                    pipelineBarLabel.textContent = d.step === 'Cancelled' ? 'Cancelled' : 'Done!';
                    if (pipelinePercent) {
                        pipelinePercent.textContent = '100%';
                        setTimeout(() => { pipelinePercent.style.display = 'none'; }, 2500);
                    }
                    setTimeout(() => {
                        pipelineBarFill.style.width = '0';
                        pipelineBarLabel.textContent = 'Scrap now 🔃';
                        pipelineBarBtn.onclick = startPipelineCb;
                        pipelineBarBtn.style.cursor = 'pointer';
                        pipelineBarBtn.disabled = false;
                        if (pipelinePercent) pipelinePercent.textContent = '0%';
                        // Force refresh to show new data after the pipeline finishes
                        window.location.reload();
                    }, 2500);
                }
            }
        }, 1200);
        return true;
    }
    return false;
}
// modules/pipeline.js
export let pipelinePolling = null;
export let pipelineRunning = false;


export async function startPipeline(pipelineBarBtn, pipelineBarFill, pipelineBarLabel, stopPipelineCb, startPipelineCb) {
    // Start a new pipeline run and start polling for progress
    if (pipelineRunning) return;
    pipelineRunning = true;
    pipelineBarBtn.disabled = true;
    pipelineBarBtn.style.cursor = 'not-allowed';
    pipelineBarBtn.style.background = '#23272f';
    pipelineBarFill.style.width = '0';
    pipelineBarLabel.textContent = 'Cancel';
    pipelineBarBtn.classList.add('pipeline-running');
    const pipelinePercent = document.getElementById('pipeline-percent');
    if (pipelinePercent) {
        pipelinePercent.textContent = '0%';
        pipelinePercent.style.display = 'inline';
    }
    // Stream logs while the pipeline is running
    showPipelineLogs();
    streamPipelineLogs();
    await fetch('/api/run-pipeline', { method: 'POST' });
    pipelineBarBtn.onclick = stopPipelineCb;
    // Poll for status updates
    pipelinePolling = setInterval(async () => {
        const statusResp = await fetch('/api/pipeline-status');
        if (statusResp.ok) {
            const data = await statusResp.json();
            pipelineBarFill.style.width = data.percent + '%';
            pipelineBarLabel.textContent = `${data.step || ''}`;
            if (pipelinePercent) pipelinePercent.textContent = `${data.percent}%`;
            if (data.percent >= 100 || data.step === 'Cancelled') {
                clearInterval(pipelinePolling);
                pipelineBarBtn.onclick = null;
                pipelineBarBtn.style.cursor = 'default';
                pipelineBarBtn.disabled = true;
                pipelineRunning = false;
                pipelineBarLabel.textContent = data.step === 'Cancelled' ? 'Cancelled' : 'Done!';
                if (pipelinePercent) {
                    pipelinePercent.textContent = '100%';
                    setTimeout(() => { pipelinePercent.style.display = 'none'; }, 2500);
                }
                setTimeout(() => {
                    pipelineBarFill.style.width = '0';
                    pipelineBarLabel.textContent = 'Run pipeline 🔃';
                    pipelineBarBtn.onclick = startPipelineCb;
                    pipelineBarBtn.style.cursor = 'pointer';
                    pipelineBarBtn.disabled = false;
                    if (pipelinePercent) pipelinePercent.textContent = '0%';
                    stopPipelineLogs();
                    // Refresh the page to show new data after completion
                    window.location.reload();
                }, 2500);
            }
        }
    }, 1200);
}

export async function stopPipeline(pipelineBarBtn, pipelineBarLabel) {
    // Cancel a running pipeline
    console.log('[Pipeline] stopPipeline appelé, pipelineRunning =', pipelineRunning);
    if (!pipelineRunning) return;
    pipelineBarBtn.onclick = null;
    pipelineBarBtn.disabled = true;
    pipelineBarLabel.textContent = 'Cancelling...';
    try {
        const resp = await fetch('/api/stop-pipeline', { method: 'POST' });
        console.log('[Pipeline] Requête /api/stop-pipeline envoyée, status:', resp.status);
    } catch (e) {
        console.error('[Pipeline] Erreur lors de l\'envoi de /api/stop-pipeline', e);
    }
    pipelineRunning = false;
}
