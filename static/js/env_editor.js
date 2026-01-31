// JavaScript for env_editor.html
// Handles editing environment variables and generating Telegram sessions

// --- Dynamic sources management ---
function renderSources(sources) {
    // Render the editable list of Telegram sources
    const list = document.getElementById('sources-list');
    list.innerHTML = '';
    sources.forEach((src, idx) => {
        const row = document.createElement('div');
        row.style = 'display:flex; gap:8px; align-items:center; margin-bottom:8px;';
        const labelInput = document.createElement('input');
        labelInput.type = 'text';
        labelInput.placeholder = 'Label';
        labelInput.value = src.label || '';
        labelInput.name = `sources[${idx}][label]`;
        labelInput.style = 'flex:1;';
        const sourceInput = document.createElement('input');
        sourceInput.type = 'text';
        sourceInput.placeholder = 'Source (URL, ID...)';
        sourceInput.value = src.value || '';
        sourceInput.name = `sources[${idx}][value]`;
        sourceInput.style = 'flex:2;';
        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.textContent = '✖';
        delBtn.title = 'Supprimer';
        delBtn.style = 'background:none; color:#f87171; border:none; font-size:1.2em; cursor:pointer;';
        delBtn.onclick = () => {
            sources.splice(idx, 1);
            renderSources(sources);
        };
        row.appendChild(labelInput);
        row.appendChild(sourceInput);
        row.appendChild(delBtn);
        list.appendChild(row);
    });
}

let sourcesData = [];

// Label mapping for dynamic form fields
const LABELS = {
    TELEGRAM_SESSION: "Session Telegram 🤖",
    SOURCES_TELEGRAM: "Telegram Sources 📡",
    OPENAI_API_KEY: "OpenAI API Key / LM Studio Key 🗝️",
    OPENAI_MODEL: "OpenAI Model / LM Studio 🧠",
    TELEGRAM_API_ID: "Telegram API ID 🆔",
    TELEGRAM_API_HASH: "Telegram API Hash 🔐",
    DB_URL: "Database URL 🔗",
    MAX_MESSAGES_PER_CHANNEL: "Scrap size 📨",
    BATCH_SIZE: "Batch Size 📦",
    TARGET_LANGUAGE: "Target Language 🌐",
    FETCH_WINDOW_HOURS: "Fetch Window (hours) ⏳",
    AUTO_DELETE_DAYS: "Auto-delete Messages (days) 🗑️",
};

// Contextual help text for each field
const LABEL_HELP = {
    TELEGRAM_SESSION: "Paste here your Telegram session string.",
    OPENAI_API_KEY: "Enter your OpenAI API or LM Studio key.",
    OPENAI_MODEL: "Specify the model name",
    TELEGRAM_API_ID: "Get your API ID https://my.telegram.org.",
    TELEGRAM_API_HASH: "Get your API Hash https://my.telegram.org.",
    DB_URL: "(Optional) Database URL",
    MAX_MESSAGES_PER_CHANNEL: "Max number of msg to fetch per channel.",
    BATCH_SIZE: "Number of messages processed per batch.",
    TARGET_LANGUAGE: "Target language for translation.",
    FETCH_WINDOW_HOURS: "Number of hours back to fetch messages from.",
    AUTO_DELETE_DAYS: "Delete messages older than X days.",
    SOURCES_TELEGRAM: "Add a source and choose a label for it.",
};

async function loadEnv() {
    // Load .env values from the API and render inputs
    const resp = await fetch('/api/env');
    const data = await resp.json();
    const fields = document.getElementById('env-fields');
    fields.innerHTML = '';
    // Parse SOURCES_TELEGRAM (CSV: source:label,...)
    let sourcesRaw = data.SOURCES_TELEGRAM;
    if (sourcesRaw) {
        sourcesData = sourcesRaw.split(',').map(pair => {
            const [source, label] = pair.split(':');
            return { value: source || '', label: label || '' };
        }).filter(s => s.value);
    } else {
        sourcesData = [];
    }
    renderSources(sourcesData);
    Object.entries(data).forEach(([key, value]) => {
        // Skip fields that are handled in the right-hand column
        if ([
            'TELEGRAM_SESSION',
            'TELEGRAM_API_ID',
            'TELEGRAM_API_HASH',
            'SOURCES_TELEGRAM'
        ].includes(key)) {
            // Still populate the static inputs when present
            if (key === 'TELEGRAM_SESSION') document.getElementById('TELEGRAM_SESSION').value = value || '';
            if (key === 'TELEGRAM_API_ID') document.getElementById('TELEGRAM_API_ID').value = value || '';
            if (key === 'TELEGRAM_API_HASH') document.getElementById('TELEGRAM_API_HASH').value = value || '';
            return;
        }
        const label = document.createElement('label');
        label.textContent = LABELS[key] || key;
        // Append contextual help next to the label
        if (LABEL_HELP[key]) {
            const help = document.createElement('span');
            help.textContent = '  ' + LABEL_HELP[key];
            help.style = 'font-size: 0.78em; color: #b7b7b7; opacity: 0.55; margin-left: 10px; vertical-align: middle; white-space: normal; display: inline-block; max-width: 320px;';
            label.appendChild(help);
        }
        fields.appendChild(label);
        const input = document.createElement('input');
        input.type = 'text';
        input.name = key;
        input.value = value || '';
        fields.appendChild(input);
    });
}

document.addEventListener('DOMContentLoaded', function() {
        // Wire up "clear database" button
        const clearBtn = document.getElementById('clear-db-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', async function() {
                if (!confirm("Effacer toute la base de données ? Cette action est irréversible.")) return;
                const success = document.getElementById('clear-db-success');
                const error = document.getElementById('clear-db-error');
                success.style.display = 'none';
                error.style.display = 'none';
                try {
                    const resp = await fetch('/api/admin/clear-db', { method: 'POST' });
                    if (resp.ok) {
                        const data = await resp.json();
                        success.textContent = data.message || 'Base effacée.';
                        success.style.display = 'block';
                    } else {
                        const err = await resp.json();
                        error.textContent = err.detail || "Erreur lors de l'effacement.";
                        error.style.display = 'block';
                    }
                } catch (e) {
                    error.textContent = "Erreur lors de l'effacement.";
                    error.style.display = 'block';
                }
            });
        }
    // Inject help text for the static Telegram session label
    const telegramLabel = document.querySelector('#session-string-row label[for="TELEGRAM_SESSION"]');
    if (telegramLabel && LABEL_HELP.TELEGRAM_SESSION) {
        const help = document.createElement('span');
        help.textContent = '  ' + LABEL_HELP.TELEGRAM_SESSION;
        help.style = 'font-size: 0.78em; color: #b7b7b7; opacity: 0.55; margin-left: 10px; vertical-align: middle; white-space: normal; display: inline-block; max-width: 320px;';
        telegramLabel.appendChild(help);
    }
    // Injecte l'aide contextuelle sur le label statique Sources
    const sourcesSection = document.getElementById('sources-section');
    const sourcesLabel = sourcesSection ? sourcesSection.querySelector('label') : null;
    if (sourcesLabel && LABEL_HELP.SOURCES_TELEGRAM) {
        const help = document.createElement('span');
        help.textContent = '  ' + LABEL_HELP.SOURCES_TELEGRAM;
        help.style = 'font-size: 0.78em; color: #b7b7b7; opacity: 0.55; margin-left: 10px; vertical-align: middle; white-space: normal; display: inline-block; max-width: 320px;';
        sourcesLabel.appendChild(help);
    }
    // Add a new empty source row
    document.getElementById('add-source-btn').addEventListener('click', function() {
        sourcesData.push({ label: '', value: '' });
        renderSources(sourcesData);
    });
    // Telegram session wizard: request code then verify
    document.getElementById('wizard-start-btn').addEventListener('click', function() {
        const wizard = document.getElementById('wizard-step');
        wizard.innerHTML = '';
        // Step 1: phone input
        const phoneInput = document.createElement('input');
        phoneInput.type = 'text';
        phoneInput.placeholder = 'Numéro de téléphone (ex: +33612345678)';
        phoneInput.style = 'width: 70%; padding: 6px; margin-right: 8px;';
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Envoyer code';
        nextBtn.type = 'button';
        nextBtn.style = 'padding:6px 14px; background:#1a1f24; color:#22c55e; border:1px solid #444; border-radius:6px; font-size:13px; cursor:pointer;';
        wizard.appendChild(phoneInput);
        wizard.appendChild(nextBtn);
        let sessionId = null;
        nextBtn.onclick = async function() {
            nextBtn.disabled = true;
            nextBtn.textContent = 'Envoi...';
            try {
                const resp = await fetch('/api/session/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone: phoneInput.value })
                });
                if (resp.ok) {
                    const data = await resp.json();
                    sessionId = data.session_id;
                    // Step 2: code input
                    wizard.innerHTML = '';
                    const codeInput = document.createElement('input');
                    codeInput.type = 'text';
                    codeInput.placeholder = 'Code reçu';
                    codeInput.style = 'width: 40%; padding: 6px; margin-right: 8px;';
                    const codeBtn = document.createElement('button');
                    codeBtn.textContent = 'Valider code';
                    codeBtn.type = 'button';
                    codeBtn.style = 'padding:6px 14px; background:#1a1f24; color:#22c55e; border:1px solid #444; border-radius:6px; font-size:13px; cursor:pointer;';
                    wizard.appendChild(codeInput);
                    wizard.appendChild(codeBtn);
                    codeBtn.onclick = async function() {
                        codeBtn.disabled = true;
                        codeBtn.textContent = 'Validation...';
                        try {
                            const resp2 = await fetch('/api/session/verify', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ session_id: sessionId, phone: phoneInput.value, code: codeInput.value })
                            });
                            if (resp2.ok) {
                                const data2 = await resp2.json();
                                document.getElementById('TELEGRAM_SESSION').value = data2.session_string || '';
                                // Save to .env directly
                                if (data2.session_string) {
                                    try {
                                        const saveResp = await fetch('/api/env', {
                                            method: 'POST',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({ TELEGRAM_SESSION: data2.session_string })
                                        });
                                        if (saveResp.ok) {
                                            wizard.innerHTML = '<span style="color:#22c55e;">Session string générée, insérée et enregistrée !</span>';
                                        } else {
                                            wizard.innerHTML = '<span style="color:#f87171;">Session générée mais erreur lors de l\'enregistrement !</span>';
                                        }
                                    } catch (e) {
                                        wizard.innerHTML = '<span style="color:#f87171;">Session générée mais erreur lors de l\'enregistrement !</span>';
                                    }
                                } else {
                                    wizard.innerHTML = '<span style="color:#f87171;">Session string vide !</span>';
                                }
                            } else {
                                wizard.innerHTML = '<span style="color:#f87171;">Erreur lors de la validation du code.</span>';
                            }
                        } catch (e) {
                            wizard.innerHTML = '<span style="color:#f87171;">Erreur lors de la validation du code.</span>';
                        }
                    };
                } else {
                    wizard.innerHTML = '<span style="color:#f87171;">Erreur lors de l’envoi du code.</span>';
                }
            } catch (e) {
                wizard.innerHTML = '<span style="color:#f87171;">Erreur lors de l’envoi du code.</span>';
            }
        };
    });
    // Submit the env form with SOURCES_TELEGRAM composed from the dynamic rows
    document.getElementById('env-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const form = e.target;
        const data = {};
        Array.from(form.elements).forEach(el => {
            if (el.name && !el.name.startsWith('sources[')) data[el.name] = el.value;
        });
        // Encode sources to CSV for SOURCES_TELEGRAM
        data.SOURCES_TELEGRAM = sourcesData.map((src, idx) => {
            // Read the current input values to avoid stale closures
            const label = form.querySelector(`input[name="sources[${idx}][label]"]`)?.value || '';
            const value = form.querySelector(`input[name="sources[${idx}][value]"]`)?.value || '';
            return value ? `${value}:${label}` : '';
        }).filter(Boolean).join(',');
        const resp = await fetch('/api/env', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const success = document.getElementById('env-success');
        const error = document.getElementById('env-error');
        if (resp.ok) {
            success.textContent = 'Modifications enregistrées !';
            success.style.display = 'block';
            error.style.display = 'none';
        } else {
            error.textContent = "Erreur lors de l'enregistrement.";
            error.style.display = 'block';
            success.style.display = 'none';
        }
    });
    // Force a full dashboard reload to ensure fresh pipeline JS state
    document.getElementById('dashboard-link').addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = '/dashboard';
    });
    loadEnv();
});
