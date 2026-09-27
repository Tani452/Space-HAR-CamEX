const currentStepTitleEl = document.getElementById('current-step-title');
const currentStepDescEl = document.getElementById('current-step-desc');
const nextStepTitleEl = document.getElementById('next-step-title');
const alertsPanelEl = document.getElementById('alerts-panel');
const alertsFeedEl = document.getElementById('alerts-feed');
const logFeedEl = document.getElementById('log-feed');
const progressContainerEl = document.getElementById('progress-container');

let previousCompletedCount = 0;
let previousViolationMessage = null;

// Text-to-speech utility
function speak(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Interrupt ongoing speech
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    }
}

// Render the progress bar dynamically based on the total steps
function renderProgress(state) {
    if (!state.all_steps) return;
    
    progressContainerEl.innerHTML = '';
    state.all_steps.forEach(step => {
        const stepEl = document.createElement('div');
        stepEl.classList.add('progress-step');
        stepEl.innerText = step.id;
        
        if (state.completed_steps.includes(step.id)) {
            stepEl.classList.add('completed');
        } else if (state.current_step && state.current_step.id === step.id) {
            stepEl.classList.add('current');
        }
        
        progressContainerEl.appendChild(stepEl);
    });
}

// WebSocket setup
function connectWebSocket() {
    const wsUrl = `ws://${location.host}/ws/state`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = function(event) {
        const state = JSON.parse(event.data);
        
        renderProgress(state);
        
        // Handle Current & Next Steps cards
        if (state.completed) {
            currentStepTitleEl.innerHTML = '<span style="color: var(--success-green);">Experiment Complete!</span>';
            currentStepDescEl.innerText = 'All steps finished successfully.';
            nextStepTitleEl.innerText = '--';
        } else {
            currentStepTitleEl.innerText = state.current_step ? state.current_step.description : '--';
            currentStepDescEl.innerText = state.current_step ? `Expected action: ${state.current_step.expected_activity}` : '--';
            nextStepTitleEl.innerText = state.next_step ? state.next_step.description : '--';
        }
        
        // Speak completion notifications
        if (state.completed_steps.length > previousCompletedCount) {
            previousCompletedCount = state.completed_steps.length;
            if (state.completed) {
                speak("Experiment complete!");
            } else if (state.current_step) {
                speak("Step complete. Next step: " + state.current_step.description);
            }
        }

        // Handle Alerts Card
        if (state.last_violation) {
            const violationMsg = state.last_violation.message;
            const violationType = state.last_violation.type; 
            
            alertsFeedEl.innerHTML = `
                <p style="color: var(--error-red); margin: 0; font-weight: bold;">${violationType.toUpperCase()}</p>
                <p style="margin: 4px 0 0 0; font-size: 0.9rem;">${violationMsg}</p>
            `;
            alertsPanelEl.classList.add('active-violation');
            
            if (violationMsg !== previousViolationMessage) {
                const readableType = violationType.replace(/_/g, ' ');
                speak(`Warning: ${readableType}. ${violationMsg}`);
                previousViolationMessage = violationMsg;
            }
        } else {
            alertsFeedEl.innerHTML = '<p class="muted">No active violations.</p>';
            alertsPanelEl.classList.remove('active-violation');
            previousViolationMessage = null; 
        }
        
        // Fetch logs on state update
        fetchLogs();
    };

    ws.onclose = function() {
        alertsFeedEl.innerHTML = '<p style="color: var(--warning-orange);">WebSocket disconnected. Retrying...</p>';
        setTimeout(connectWebSocket, 2000); // Auto-reconnect
    };
}

// Fetch logs from REST endpoint
async function fetchLogs() {
    try {
        const response = await fetch('/log');
        const data = await response.json();
        
        logFeedEl.innerHTML = '';
        
        // Show all logs in the file
        const recentLogs = data.logs;
        if (recentLogs.length === 0) {
            logFeedEl.innerHTML = '<p class="muted">System initialized.</p>';
        } else {
            recentLogs.forEach(entry => {
                const timeStr = new Date(entry.timestamp * 1000).toLocaleTimeString([], { hour12: false });
                const isSuccess = entry.status === 'completed';
                const statusClass = isSuccess ? 'log-status-completed' : 'log-status-error';
                
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                logEntry.innerHTML = `<span class="log-time">[${timeStr}]</span> <span class="${statusClass}">${entry.status.toUpperCase()}</span>: ${entry.message}`;
                logFeedEl.appendChild(logEntry);
            });
            // Auto scroll to bottom
            logFeedEl.scrollTop = logFeedEl.scrollHeight;
        }
    } catch (e) {
        console.error("Error fetching logs", e);
    }
}

// Reset Button Logic
document.getElementById('reset-btn').addEventListener('click', async () => {
    try {
        const response = await fetch('/reset', { method: 'POST' });
        if (response.ok) {
            speak("Experiment reset.");
        }
    } catch (e) {
        console.error("Failed to reset experiment", e);
    }
});

// Modal Logic
const refModal = document.getElementById('ref-modal');
document.getElementById('manage-objects-btn').addEventListener('click', () => {
    refModal.classList.add('show');
});
document.getElementById('close-modal-btn').addEventListener('click', () => {
    refModal.classList.remove('show');
});
window.addEventListener('click', (e) => {
    if (e.target === refModal) {
        refModal.classList.remove('show');
    }
});

// ----------------- REFERENCE OBJECTS LOGIC ----------------- //
async function fetchReferences() {
    try {
        const res = await fetch('/reference/list');
        const data = await res.json();
        const listEl = document.getElementById('ref-list');
        listEl.innerHTML = '';
        
        if (Object.keys(data).length === 0) {
            listEl.innerHTML = '<li class="muted">No reference objects defined.</li>';
            return;
        }
        
        for (const [label, count] of Object.entries(data)) {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.padding = '4px 8px';
            li.style.background = 'var(--bg-dark)';
            li.style.borderRadius = '4px';
            li.style.marginBottom = '4px';
            
            li.innerHTML = `
                <span><strong>${label}</strong> <span class="muted" style="font-size: 0.8rem;">(${count} imgs)</span></span>
                <button onclick="deleteReference('${label}')" style="background: var(--error-red); border: none; color: white; border-radius: 3px; cursor: pointer; padding: 2px 6px;">Delete</button>
            `;
            listEl.appendChild(li);
        }
    } catch (e) {
        console.error('Failed to fetch references', e);
    }
}

// Expose to global scope for inline onclick handler
window.deleteReference = async function(label) {
    if (!confirm(`Delete all reference images for '${label}'?`)) return;
    try {
        await fetch(`/reference/${label}`, { method: 'DELETE' });
        fetchReferences();
    } catch (e) {
        console.error('Failed to delete reference', e);
    }
};

document.getElementById('upload-ref-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const labelInput = document.getElementById('ref-label');
    const fileInput = document.getElementById('ref-file');
    
    if (!fileInput.files[0]) return;
    
    const formData = new FormData();
    formData.append('label', labelInput.value.trim().toLowerCase());
    formData.append('file', fileInput.files[0]);
    
    const btn = e.target.querySelector('button');
    btn.innerText = 'Uploading...';
    btn.disabled = true;
    
    try {
        await fetch('/reference/upload', {
            method: 'POST',
            body: formData
        });
        labelInput.value = '';
        fileInput.value = '';
        fetchReferences();
    } catch (err) {
        console.error('Failed to upload', err);
        alert('Upload failed.');
    } finally {
        btn.innerText = 'Upload & Train';
        btn.disabled = false;
    }
});

// Initial initialization
fetchLogs();
fetchReferences();
connectWebSocket();

// Allow audio to unlock on first click anywhere
document.body.addEventListener('click', () => {
    if ('speechSynthesis' in window) {
        const u = new SpeechSynthesisUtterance('');
        u.volume = 0;
        window.speechSynthesis.speak(u);
    }
}, { once: true });
