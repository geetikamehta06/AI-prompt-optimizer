/**
 * Enterprise Prompt — Main Application
 * 
 * Single-page application with client-side routing, API integration,
 * and real-time SSE streaming for prompt enhancement.
 */

(function () {
    'use strict';

    // ── State ──────────────────────────────────────────────
    const state = {
        currentPage: 'dashboard',
        frameworks: [],
        isEnhancing: false,
    };

    // ── API Client ─────────────────────────────────────────
    const api = {
        async get(url) {
            const res = await fetch(url);
            return res.json();
        },
        async post(url, data) {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            return res.json();
        },
        async del(url) {
            const res = await fetch(url, { method: 'DELETE' });
            return res.json();
        },
        streamEnhance(data) {
            return fetch('/api/enhance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
        }
    };

    // ── Toast Notifications ────────────────────────────────
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icons = { success: '✅', error: '❌', info: 'ℹ️' };
        toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span class="toast-message">${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateX(100%)'; setTimeout(() => toast.remove(), 300); }, 4000);
    }

    // ── Router ─────────────────────────────────────────────
    function navigate(page) {
        state.currentPage = page;
        // Update nav
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
        if (navItem) navItem.classList.add('active');

        // Update pages
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const pageEl = document.getElementById(`page-${page}`);
        if (pageEl) pageEl.classList.add('active');

        // Update header
        const titles = { dashboard: 'Dashboard', enhance: 'Enhance Prompt', playground: 'Playground', frameworks: 'Framework Explorer', history: 'Prompt History', settings: 'Settings' };
        document.getElementById('header-title').textContent = titles[page] || page;

        // Load page data
        if (page === 'dashboard') loadDashboard();
        if (page === 'frameworks') loadFrameworks();
        if (page === 'history') loadHistory();
    }

    // ── Dashboard ──────────────────────────────────────────
    async function loadDashboard() {
        try {
            const data = await api.get('/api/analytics');
            document.getElementById('stat-total').textContent = data.total_prompts || 0;
            document.getElementById('stat-improvement').textContent = `+${data.avg_quality_improvement || 0}`;
            document.getElementById('stat-today').textContent = data.prompts_today || 0;
            if (data.top_frameworks && data.top_frameworks.length > 0) {
                document.getElementById('stat-top-fw').textContent = data.top_frameworks[0].id.toUpperCase();
            }

            // Load recent activity
            const history = await api.get('/api/history?limit=5');
            const actDiv = document.getElementById('recent-activity');
            if (history && history.length > 0) {
                actDiv.innerHTML = history.map(item => `
                    <div class="flex items-center justify-between" style="padding:var(--space-3) 0; border-bottom:var(--border-subtle);">
                        <div>
                            <div class="text-sm" style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(item.original_text || '')}</div>
                            <div class="text-xs text-secondary">${item.frameworks_used || '—'}</div>
                        </div>
                        <span class="badge badge-success">${item.quality_after ? Math.round(item.quality_after) : '—'}</span>
                    </div>
                `).join('');
            }

            // Framework usage
            const usageDiv = document.getElementById('framework-usage');
            if (data.top_frameworks && data.top_frameworks.length > 0) {
                const maxCount = data.top_frameworks[0].count;
                usageDiv.innerHTML = data.top_frameworks.map(fw => `
                    <div style="margin-bottom:var(--space-3);">
                        <div class="flex justify-between text-sm mb-4">
                            <span>${fw.id.toUpperCase()}</span>
                            <span class="text-secondary">${fw.count} uses</span>
                        </div>
                        <div class="progress-bar"><div class="progress-bar-fill" style="width:${(fw.count / maxCount * 100)}%"></div></div>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error('Dashboard load error:', e);
        }
    }

    // ── Enhance ────────────────────────────────────────────
    async function enhancePrompt(promptText) {
        if (state.isEnhancing || !promptText.trim()) return;
        state.isEnhancing = true;

        const enhanceBtn = document.getElementById('enhance-btn');
        const quickBtn = document.getElementById('quick-enhance-btn');
        if (enhanceBtn) { enhanceBtn.disabled = true; enhanceBtn.innerHTML = '<span class="spinner"></span> Enhancing...'; }
        if (quickBtn) { quickBtn.disabled = true; }

        // Show pipeline progress
        const progressEl = document.getElementById('pipeline-progress');
        if (progressEl) progressEl.style.display = 'block';
        const qualComp = document.getElementById('quality-comparison');
        if (qualComp) qualComp.style.display = 'none';
        const detailsEl = document.getElementById('enhancement-details');
        if (detailsEl) detailsEl.style.display = 'none';

        // Reset pipeline stages
        document.querySelectorAll('.pipeline-stage').forEach(s => { s.classList.remove('completed', 'active'); });

        const outputEl = document.getElementById('prompt-output');
        if (outputEl) { outputEl.textContent = 'Enhancing...'; outputEl.classList.remove('empty'); }

        const data = {
            prompt: promptText,
            framework_id: document.getElementById('framework-select')?.value || null,
            provider: document.getElementById('provider-select')?.value || null,
            enable_evaluation: document.getElementById('eval-toggle')?.checked ?? true,
            enable_refinement: document.getElementById('refine-toggle')?.checked ?? true,
        };

        try {
            const response = await api.streamEnhance(data);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            const stageMap = { 'Sanitizing': 0, 'Analyzing': 1, 'Selecting Framework': 2, 'Enhancing': 3, 'Evaluating': 4, 'Refining': 5, 'Complete': 6 };
            const stages = document.querySelectorAll('.pipeline-stage');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const event = JSON.parse(line.slice(6));

                        // Update pipeline visualization
                        if (event.stage && stageMap[event.stage] !== undefined) {
                            const idx = stageMap[event.stage];
                            stages.forEach((s, i) => {
                                if (i < idx) s.classList.add('completed');
                                else s.classList.remove('completed');
                                s.classList.toggle('active', i === idx);
                            });
                        }

                        // Update log
                        if (event.log) {
                            const logEl = document.getElementById('pipeline-log');
                            if (logEl) logEl.textContent = event.log;
                        }

                        // Handle completion
                        if (event.complete && event.result) {
                            const result = event.result;
                            if (outputEl) {
                                outputEl.textContent = result.enhanced_prompt;
                                outputEl.classList.remove('empty');
                            }

                            // Show copy button
                            const copyBtn = document.getElementById('copy-btn');
                            if (copyBtn) copyBtn.style.display = 'inline-flex';

                            // Show quality comparison
                            if (result.quality_before !== null && result.quality_after !== null) {
                                if (qualComp) {
                                    qualComp.style.display = 'flex';
                                    document.getElementById('score-before').textContent = Math.round(result.quality_before);
                                    document.getElementById('score-after').textContent = Math.round(result.quality_after);
                                }
                            }

                            // Show enhancement details
                            if (detailsEl) {
                                detailsEl.style.display = 'block';
                                document.getElementById('enhancement-info').innerHTML = `
                                    <div class="grid grid-3 gap-4">
                                        <div><div class="text-xs text-secondary">Frameworks Used</div><div class="text-sm mt-4">${(result.frameworks_used || []).map(f => `<span class="badge badge-primary" style="margin-right:4px;">${f.toUpperCase()}</span>`).join('')}</div></div>
                                        <div><div class="text-xs text-secondary">Provider / Model</div><div class="text-sm mt-4">${result.provider_used || '—'} / ${result.model_used || '—'}</div></div>
                                        <div><div class="text-xs text-secondary">Processing Time</div><div class="text-sm mt-4">${(result.processing_time_ms / 1000).toFixed(1)}s</div></div>
                                    </div>
                                    ${result.improvement_summary ? `<div class="mt-4"><div class="text-xs text-secondary">Improvement Summary</div><div class="text-sm mt-4">${escapeHtml(result.improvement_summary)}</div></div>` : ''}
                                    ${result.reasoning ? `<div class="mt-4"><div class="text-xs text-secondary">Reasoning</div><div class="text-sm mt-4">${escapeHtml(result.reasoning)}</div></div>` : ''}
                                `;
                            }

                            // Mark all stages complete
                            stages.forEach(s => { s.classList.add('completed'); s.classList.remove('active'); });

                            showToast('Prompt enhanced successfully!', 'success');
                        }

                        // Handle error
                        if (event.error) {
                            showToast(`Error: ${event.error}`, 'error');
                            if (outputEl) { outputEl.textContent = `Error: ${event.error}`; outputEl.classList.remove('empty'); }
                        }
                    } catch (parseErr) { /* ignore non-JSON lines */ }
                }
            }
        } catch (err) {
            showToast(`Enhancement failed: ${err.message}`, 'error');
            if (outputEl) { outputEl.textContent = `Error: ${err.message}`; outputEl.classList.remove('empty'); }
        } finally {
            state.isEnhancing = false;
            if (enhanceBtn) { enhanceBtn.disabled = false; enhanceBtn.innerHTML = '✨ Enhance Prompt'; }
            if (quickBtn) { quickBtn.disabled = false; }
        }
    }

    // ── Frameworks ─────────────────────────────────────────
    async function loadFrameworks() {
        try {
            state.frameworks = await api.get('/api/frameworks');
            renderFrameworks(state.frameworks);
            populateFrameworkSelects(state.frameworks);
        } catch (e) {
            console.error('Framework load error:', e);
        }
    }

    function renderFrameworks(frameworks) {
        const grid = document.getElementById('frameworks-grid');
        const countEl = document.getElementById('fw-count');
        if (!grid) return;

        const enabled = frameworks.filter(f => f.enabled);
        if (countEl) countEl.textContent = `${enabled.length} frameworks available`;

        grid.innerHTML = enabled.map(fw => `
            <div class="framework-card" data-fw-id="${fw.id}">
                <div class="fw-acronym">${fw.category.replace('_', ' ')}</div>
                <div class="fw-name">${fw.name}</div>
                <div class="fw-desc">${fw.description}</div>
                <div class="fw-fields">${fw.fields.map(f => `<span class="badge badge-primary">${f.name}</span>`).join('')}</div>
                <div class="fw-tags">${fw.best_for.map(t => `<span class="badge badge-info">${t}</span>`).join('')}</div>
                <div class="flex justify-between items-center mt-4">
                    <span class="badge ${fw.complexity === 'simple' ? 'badge-success' : fw.complexity === 'advanced' ? 'badge-warning' : 'badge-info'}">${fw.complexity}</span>
                    <button class="btn btn-sm btn-ghost" onclick="window.EP.useFramework('${fw.id}')">Use →</button>
                </div>
            </div>
        `).join('');
    }

    function populateFrameworkSelects(frameworks) {
        const selects = [
            document.getElementById('framework-select'),
            document.getElementById('playground-fw-a'),
            document.getElementById('playground-fw-b'),
        ];
        selects.forEach(sel => {
            if (!sel) return;
            const first = sel.options[0];
            sel.innerHTML = '';
            sel.appendChild(first);
            frameworks.filter(f => f.enabled).forEach(fw => {
                const opt = document.createElement('option');
                opt.value = fw.id;
                opt.textContent = `${fw.name} (${fw.id.toUpperCase()})`;
                sel.appendChild(opt);
            });
        });
    }

    // ── History ────────────────────────────────────────────
    async function loadHistory() {
        try {
            const items = await api.get('/api/history?limit=50');
            const tbody = document.getElementById('history-body');
            const emptyEl = document.getElementById('history-empty');
            const tableEl = document.getElementById('history-table');
            if (!tbody) return;

            if (!items || items.length === 0) {
                if (emptyEl) emptyEl.style.display = 'block';
                if (tableEl) tableEl.style.display = 'none';
                return;
            }
            if (emptyEl) emptyEl.style.display = 'none';
            if (tableEl) tableEl.style.display = 'table';

            tbody.innerHTML = items.map(item => {
                let fws = '—';
                try { fws = JSON.parse(item.frameworks_used || '[]').map(f => f.toUpperCase()).join(', '); } catch(e) {}
                const date = item.created_at ? new Date(item.created_at).toLocaleDateString() : '—';
                const quality = item.quality_after ? Math.round(item.quality_after) : '—';
                return `
                    <tr>
                        <td class="prompt-preview">${escapeHtml(item.original_text || '')}</td>
                        <td><span class="badge badge-primary">${fws}</span></td>
                        <td><span class="badge badge-success">${quality}</span></td>
                        <td class="text-secondary">${date}</td>
                        <td>
                            <button class="btn btn-ghost btn-sm" onclick="window.EP.viewPrompt('${item.id}')">View</button>
                            <button class="btn btn-danger btn-sm" onclick="window.EP.deletePrompt('${item.id}')">×</button>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (e) {
            console.error('History load error:', e);
        }
    }

    // ── Playground ─────────────────────────────────────────
    async function runPlayground(panel) {
        const inputEl = document.getElementById('playground-input');
        const fwSelect = document.getElementById(`playground-fw-${panel}`);
        const outputEl = document.getElementById(`playground-output-${panel}`);
        const scoreEl = document.getElementById(`playground-score-${panel}`);
        const btnEl = document.getElementById(`playground-run-${panel}`);
        if (!inputEl || !inputEl.value.trim()) { showToast('Enter a prompt first', 'error'); return; }

        btnEl.disabled = true;
        btnEl.innerHTML = '<span class="spinner"></span>';
        outputEl.textContent = 'Enhancing...';
        outputEl.classList.remove('empty');

        try {
            const response = await api.streamEnhance({
                prompt: inputEl.value,
                framework_id: fwSelect?.value || null,
                enable_evaluation: true,
                enable_refinement: false,
            });
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const event = JSON.parse(line.slice(6));
                        if (event.complete && event.result) {
                            outputEl.textContent = event.result.enhanced_prompt;
                            scoreEl.textContent = event.result.quality_after ? `Score: ${Math.round(event.result.quality_after)}` : '—';
                        }
                        if (event.error) {
                            outputEl.textContent = `Error: ${event.error}`;
                        }
                    } catch (e) {}
                }
            }
        } catch (e) {
            outputEl.textContent = `Error: ${e.message}`;
        } finally {
            btnEl.disabled = false;
            btnEl.textContent = `Run ${panel.toUpperCase()}`;
        }
    }

    // ── Utilities ──────────────────────────────────────────
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function updateCharCount() {
        const input = document.getElementById('prompt-input');
        const counter = document.getElementById('input-char-count');
        if (input && counter) {
            const text = input.value;
            const chars = text.length;
            const words = text.trim() ? text.trim().split(/\s+/).length : 0;
            counter.textContent = `${chars} chars · ${words} words`;
        }
    }

    // ── Public API (for inline onclick handlers) ──────────
    window.EP = {
        useFramework(id) {
            navigate('enhance');
            const sel = document.getElementById('framework-select');
            if (sel) sel.value = id;
            showToast(`Framework ${id.toUpperCase()} selected`, 'info');
        },
        async viewPrompt(id) {
            try {
                const data = await api.get(`/api/history/${id}`);
                if (data.prompt) {
                    navigate('enhance');
                    const input = document.getElementById('prompt-input');
                    const output = document.getElementById('prompt-output');
                    if (input) input.value = data.prompt.original_text || '';
                    if (output) { output.textContent = data.prompt.enhanced_text || ''; output.classList.remove('empty'); }
                    updateCharCount();
                }
            } catch (e) { showToast('Failed to load prompt', 'error'); }
        },
        async deletePrompt(id) {
            if (!confirm('Delete this prompt?')) return;
            try {
                await api.del(`/api/history/${id}`);
                showToast('Prompt deleted', 'success');
                loadHistory();
            } catch (e) { showToast('Delete failed', 'error'); }
        }
    };

    // ── Event Listeners ────────────────────────────────────
    function init() {
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => navigate(item.dataset.page));
        });

        // Quick enhance
        document.getElementById('quick-enhance-btn')?.addEventListener('click', () => {
            const input = document.getElementById('quick-enhance-input');
            if (input && input.value.trim()) {
                navigate('enhance');
                document.getElementById('prompt-input').value = input.value;
                updateCharCount();
                enhancePrompt(input.value);
            }
        });

        // Quick enhance on Enter
        document.getElementById('quick-enhance-input')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') document.getElementById('quick-enhance-btn')?.click();
        });

        // Main enhance
        document.getElementById('enhance-btn')?.addEventListener('click', () => {
            const input = document.getElementById('prompt-input');
            if (input) enhancePrompt(input.value);
        });

        // Char count
        document.getElementById('prompt-input')?.addEventListener('input', updateCharCount);

        // Copy button
        document.getElementById('copy-btn')?.addEventListener('click', () => {
            const output = document.getElementById('prompt-output');
            if (output) {
                navigator.clipboard.writeText(output.textContent).then(() => showToast('Copied to clipboard!', 'success'));
            }
        });

        // Framework filters
        document.getElementById('fw-category-filter')?.addEventListener('change', (e) => {
            const cat = e.target.value;
            const filtered = cat ? state.frameworks.filter(f => f.category === cat) : state.frameworks;
            renderFrameworks(filtered);
        });

        document.getElementById('fw-search')?.addEventListener('input', (e) => {
            const q = e.target.value.toLowerCase();
            const filtered = state.frameworks.filter(f =>
                f.name.toLowerCase().includes(q) || f.description.toLowerCase().includes(q) ||
                f.best_for.some(bf => bf.toLowerCase().includes(q))
            );
            renderFrameworks(filtered);
        });

        // History refresh
        document.getElementById('refresh-history')?.addEventListener('click', loadHistory);

        // Playground
        document.getElementById('playground-run-a')?.addEventListener('click', () => runPlayground('a'));
        document.getElementById('playground-run-b')?.addEventListener('click', () => runPlayground('b'));

        // Toggle switches
        document.querySelectorAll('.toggle').forEach(toggle => {
            toggle.addEventListener('click', () => toggle.classList.toggle('active'));
        });

        // Ctrl+Enter to enhance
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && state.currentPage === 'enhance') {
                document.getElementById('enhance-btn')?.click();
            }
        });

        // Load initial data
        loadDashboard();
        loadFrameworks();
    }

    // Boot
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
