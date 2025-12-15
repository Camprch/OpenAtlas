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
    await fetch('/api/run-pipeline', { method: 'POST' });
    pipelineBarBtn.onclick = stopPipelineCb;
    pipelinePolling = setInterval(async () => {
        const statusResp = await fetch('/api/pipeline-status');
        if (statusResp.ok) {
            const data = await statusResp.json();
            pipelineBarFill.style.width = data.percent + '%';
            pipelineBarLabel.textContent = `${data.step || ''}  ${data.percent}%`;
            if (data.percent >= 100 || data.step === 'Annulé') {
                clearInterval(pipelinePolling);
                pipelineBarBtn.onclick = null;
                pipelineBarBtn.style.cursor = 'default';
                pipelineBarBtn.disabled = true;
                pipelineRunning = false;
                pipelineBarLabel.textContent = data.step === 'Annulé' ? 'Annulé' : 'Terminé !';
                setTimeout(() => {
                    pipelineBarFill.style.width = '0';
                    pipelineBarLabel.textContent = 'Scrap now 🔃';
                    pipelineBarBtn.onclick = startPipelineCb;
                    pipelineBarBtn.style.cursor = 'pointer';
                    pipelineBarBtn.disabled = false;
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
