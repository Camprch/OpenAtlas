// modules/pipeline.js
export let pipelinePolling = null;
export let pipelineRunning = false;


export async function startPipeline(pipelineBarBtn, pipelineBarFill, pipelineBarLabel, stopPipelineCb, startPipelineCb) {
    if (pipelineRunning) return;
    pipelineRunning = true;
    pipelineBarBtn.disabled = true;
    pipelineBarBtn.style.cursor = 'not-allowed';
    pipelineBarBtn.style.background = '#23272f';
    pipelineBarFill.style.width = '0';
    pipelineBarLabel.textContent = 'Annuler';
    pipelineBarBtn.classList.add('pipeline-running');
    const pipelinePercent = document.getElementById('pipeline-percent');
    if (pipelinePercent) {
        pipelinePercent.textContent = '0%';
        pipelinePercent.style.display = 'inline';
    }
    await fetch('/api/run-pipeline', { method: 'POST' });
    pipelineBarBtn.onclick = stopPipelineCb;
    pipelinePolling = setInterval(async () => {
        const statusResp = await fetch('/api/pipeline-status');
        if (statusResp.ok) {
            const data = await statusResp.json();
            pipelineBarFill.style.width = data.percent + '%';
            pipelineBarLabel.textContent = `${data.step || ''}`;
            if (pipelinePercent) pipelinePercent.textContent = `${data.percent}%`;
            if (data.percent >= 100 || data.step === 'Annulé') {
                clearInterval(pipelinePolling);
                pipelineBarBtn.onclick = null;
                pipelineBarBtn.style.cursor = 'default';
                pipelineBarBtn.disabled = true;
                pipelineRunning = false;
                pipelineBarLabel.textContent = data.step === 'Annulé' ? 'Annulé' : 'Terminé !';
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
                    // Recharge la page pour afficher les nouvelles données
                    window.location.reload();
                }, 2500);
            }
        }
    }, 1200);
}

export async function stopPipeline(pipelineBarBtn, pipelineBarLabel) {
    if (!pipelineRunning) return;
    pipelineBarBtn.onclick = null;
    pipelineBarBtn.disabled = true;
    pipelineBarLabel.textContent = 'Annulation...';
    await fetch('/api/stop-pipeline', { method: 'POST' });
    pipelineRunning = false;
}
