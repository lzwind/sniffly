/**
 * Overview page export and OpenCode display functionality
 */

let currentDataSource = 'claude';
let opencodeProjects = [];
let opencodeStats = null;
let opencodeCurrentPage = 1;
let opencodePerPage = 10;
let opencodeSortField = 'last_modified';
let opencodeSortDesc = true;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Set default export dates
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    document.getElementById('export-start-date').value = thirtyDaysAgo.toISOString().split('T')[0];
    document.getElementById('export-end-date').value = today.toISOString().split('T')[0];

    // Load OpenCode data
    loadOpenCodeData();
});

// Switch between Claude Code and OpenCode data
function switchDataSource(source) {
    currentDataSource = source;

    // Update tab styles
    document.getElementById('tab-claude').style.background = source === 'claude' ? '#667eea' : '#e5e7eb';
    document.getElementById('tab-claude').style.color = source === 'claude' ? 'white' : '#374151';
    document.getElementById('tab-opencode').style.background = source === 'opencode' ? '#667eea' : '#e5e7eb';
    document.getElementById('tab-opencode').style.color = source === 'opencode' ? 'white' : '#374151';

    // Show/hide sections
    document.getElementById('claude-section').style.display = source === 'claude' ? 'block' : 'none';
    document.getElementById('opencode-section').style.display = source === 'opencode' ? 'block' : 'none';
}

// Load OpenCode data
async function loadOpenCodeData() {
    try {
        const response = await fetch('/api/opencode/projects');
        const data = await response.json();
        opencodeProjects = (data.projects || []).map(p => ({
            ...p,
            display_name: p.name,
            session_count: p.session_count || 0,
            command_count: p.message_count || 0,
            first_used: p.first_session,
            last_modified: p.last_session,
            duration: 0,  // OpenCode doesn't track duration
            cost: null,   // OpenCode doesn't track cost
            tokens_per_cmd: 0,
            steps_per_cmd: null,  // OpenCode doesn't track steps
            cmds_per_context: null,
            books: 0,
            status: 'active'
        }));

        // Load stats for additional data
        const statsResponse = await fetch('/api/opencode/stats');
        opencodeStats = await statsResponse.json();

        // Merge stats into projects
        if (opencodeStats && opencodeStats.daily_stats) {
            // Calculate tokens per project (approximate based on total)
            const totalTokens = opencodeStats.summary?.total_tokens?.total || 0;
            const totalMsgs = opencodeStats.summary?.total_messages || 1;
            const avgTokensPerMsg = totalTokens / totalMsgs;

            opencodeProjects.forEach(p => {
                p.tokens_per_cmd = Math.round(avgTokensPerMsg);
                // Calculate books (assuming 60k words/book, ~4 chars per word, ~1.3 tokens per word)
                const outputTokens = Math.round(p.command_count * avgTokensPerMsg * 0.3);
                p.books = (outputTokens * 0.75 / 60000).toFixed(2);
            });
        }

        renderOpenCodeTable();

    } catch (e) {
        console.error('Failed to load OpenCode data:', e);
        const tbody = document.getElementById('opencode-tbody');
        tbody.textContent = '';
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 12;
        cell.style.textAlign = 'center';
        cell.style.color = '#ef4444';
        cell.textContent = '加载失败: ' + e.message;
        row.appendChild(cell);
        tbody.appendChild(row);
    }
}

// Render OpenCode table
function renderOpenCodeTable() {
    const tbody = document.getElementById('opencode-tbody');
    tbody.textContent = '';

    // Filter
    const search = (document.getElementById('opencode-search')?.value || '').toLowerCase();
    let filtered = opencodeProjects.filter(p =>
        (p.display_name || '').toLowerCase().includes(search)
    );

    // Sort
    filtered.sort((a, b) => {
        let va = a[opencodeSortField];
        let vb = b[opencodeSortField];
        if (va === null || va === undefined) va = 0;
        if (vb === null || vb === undefined) vb = 0;
        if (typeof va === 'string') va = new Date(va).getTime() || 0;
        if (typeof vb === 'string') vb = new Date(vb).getTime() || 0;
        return opencodeSortDesc ? (vb - va) : (va - vb);
    });

    // Update info
    document.getElementById('opencode-project-count-info').textContent =
        `${filtered.length} projects`;

    if (filtered.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 12;
        cell.style.textAlign = 'center';
        cell.style.color = '#6b7280';
        cell.textContent = '暂无 OpenCode 项目数据';
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    // Pagination
    const totalPages = Math.ceil(filtered.length / opencodePerPage);
    if (opencodeCurrentPage > totalPages) opencodeCurrentPage = totalPages;
    if (opencodeCurrentPage < 1) opencodeCurrentPage = 1;

    const start = (opencodeCurrentPage - 1) * opencodePerPage;
    const pageData = filtered.slice(start, start + opencodePerPage);

    pageData.forEach(project => {
        const row = document.createElement('tr');

        // Project name
        const nameCell = createCell('project-name', project.display_name || '');

        // Sessions
        const sessionCell = createCell('number', project.session_count || 0);

        // Commands
        const cmdCell = createCell('number', project.command_count || 0);

        // First Used
        const firstCell = createCell('date', project.first_used);

        // Last Active
        const lastCell = createCell('date', project.last_modified);

        // Duration (N/A for OpenCode)
        const durCell = createCell('na', null, 'N/A');

        // Cost (N/A for OpenCode)
        const costCell = createCell('na', null, 'N/A');

        // Tokens/Cmd
        const tokensCell = createCell('number', project.tokens_per_cmd || 0);

        // Steps/Cmd (N/A for OpenCode)
        const stepsCell = createCell('na', null, 'N/A');

        // Cmds/Context (N/A for OpenCode)
        const ctxCell = createCell('na', null, 'N/A');

        // Books
        const booksCell = createCell('number', project.books || 0);

        // Status
        const statusCell = createCell('status', project.status);

        [nameCell, sessionCell, cmdCell, firstCell, lastCell, durCell, costCell,
         tokensCell, stepsCell, ctxCell, booksCell, statusCell].forEach(cell => {
            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });

    // Update pagination
    updateOpenCodePagination(totalPages);

    // Update charts
    updateOpenCodeCharts();
}

function createCell(type, value, naText = null) {
    const cell = document.createElement('td');

    if (type === 'project-name') {
        const span = document.createElement('span');
        span.className = 'project-name';
        span.textContent = value;
        cell.appendChild(span);
    } else if (type === 'na') {
        const span = document.createElement('span');
        span.className = 'na-value';
        span.textContent = naText || 'N/A';
        cell.appendChild(span);
    } else if (type === 'date') {
        cell.textContent = value ? formatDate(value) : 'N/A';
    } else if (type === 'status') {
        const badge = document.createElement('span');
        badge.style.padding = '0.2rem 0.5rem';
        badge.style.borderRadius = '4px';
        badge.style.fontSize = '0.75rem';
        if (value === 'active') {
            badge.style.background = '#dcfce7';
            badge.style.color = '#166534';
            badge.textContent = 'Active';
        } else {
            badge.style.background = '#f3f4f6';
            badge.style.color = '#6b7280';
            badge.textContent = value || 'Unknown';
        }
        cell.appendChild(badge);
    } else {
        cell.textContent = typeof value === 'number' ? formatNumber(value) : (value || 0);
    }

    return cell;
}

function updateOpenCodePagination(totalPages) {
    const pagination = document.getElementById('opencode-pagination');
    if (totalPages <= 1) {
        pagination.style.display = 'none';
        return;
    }

    pagination.style.display = 'flex';
    document.getElementById('opencode-total-pages').textContent = totalPages;
    document.getElementById('opencode-page-input').value = opencodeCurrentPage;

    document.getElementById('opencode-prev-btn').disabled = opencodeCurrentPage <= 1;
    document.getElementById('opencode-next-btn').disabled = opencodeCurrentPage >= totalPages;
}

function changeOpenCodePage(delta) {
    opencodeCurrentPage += delta;
    renderOpenCodeTable();
}

function goToOpenCodePage() {
    const page = parseInt(document.getElementById('opencode-page-input').value) || 1;
    opencodeCurrentPage = page;
    renderOpenCodeTable();
}

function updateOpenCodePerPage() {
    opencodePerPage = parseInt(document.getElementById('opencode-per-page').value) || 10;
    opencodeCurrentPage = 1;
    renderOpenCodeTable();
}

function sortOpenCodeTable(field) {
    if (opencodeSortField === field) {
        opencodeSortDesc = !opencodeSortDesc;
    } else {
        opencodeSortField = field;
        opencodeSortDesc = true;
    }
    renderOpenCodeTable();
}

function filterOpenCodeProjects() {
    opencodeCurrentPage = 1;
    renderOpenCodeTable();
}

// Update OpenCode charts
function updateOpenCodeCharts() {
    if (!opencodeStats) return;

    const summary = opencodeStats.summary || {};
    const tokens = summary.total_tokens || {};

    // Update token summary
    const tokenAllTime = document.getElementById('opencode-token-all-time');
    if (tokenAllTime) {
        tokenAllTime.innerHTML = `All-time: <span class="token-input">${formatNumber(tokens.input || 0)}</span> input · <span class="token-output">${formatNumber(tokens.output || 0)}</span> output`;
    }

    // Update session summary
    const totalSessions = document.getElementById('opencode-total-sessions');
    if (totalSessions) {
        totalSessions.textContent = `Total sessions: ${summary.total_sessions || 0}`;
    }
    const totalMsgs = document.getElementById('opencode-total-messages');
    if (totalMsgs) {
        totalMsgs.textContent = `Total messages: ${summary.total_messages || 0}`;
    }

    // Token chart
    const tokenCtx = document.getElementById('opencode-token-chart');
    if (tokenCtx && opencodeStats.daily_stats) {
        new Chart(tokenCtx, {
            type: 'bar',
            data: {
                labels: opencodeStats.daily_stats.map(d => d.date),
                datasets: [
                    {
                        label: 'Input',
                        data: opencodeStats.daily_stats.map(d => d.tokens?.input || 0),
                        backgroundColor: '#667eea',
                        stack: 'tokens'
                    },
                    {
                        label: 'Output',
                        data: opencodeStats.daily_stats.map(d => d.tokens?.output || 0),
                        backgroundColor: '#764ba2',
                        stack: 'tokens'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true }
                },
                plugins: {
                    legend: { position: 'top' }
                }
            }
        });
    }

    // Session chart
    const sessionCtx = document.getElementById('opencode-session-chart');
    if (sessionCtx && opencodeStats.daily_stats) {
        new Chart(sessionCtx, {
            type: 'line',
            data: {
                labels: opencodeStats.daily_stats.map(d => d.date),
                datasets: [
                    {
                        label: 'Sessions',
                        data: opencodeStats.daily_stats.map(d => d.sessions || 0),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Messages',
                        data: opencodeStats.daily_stats.map(d => d.messages || 0),
                        borderColor: '#764ba2',
                        backgroundColor: 'rgba(118, 75, 162, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                },
                plugins: {
                    legend: { position: 'top' }
                }
            }
        });
    }
}

// Show export modal
function showExportModal() {
    // Populate project dropdown
    const projectSelect = document.getElementById('export-project');
    projectSelect.innerHTML = '<option value="">所有项目</option>';

    // Add projects based on current data source
    const source = document.getElementById('export-source').value;
    if (source === 'claude' || source === 'both') {
        // Get Claude projects from overview.js
        if (typeof allProjects !== 'undefined') {
            allProjects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = `claude:${p.display_name}`;
                opt.textContent = `[Claude] ${p.display_name}`;
                projectSelect.appendChild(opt);
            });
        }
    }
    if (source === 'opencode' || source === 'both') {
        opencodeProjects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = `opencode:${p.display_name}`;
            opt.textContent = `[OpenCode] ${p.display_name}`;
            projectSelect.appendChild(opt);
        });
    }

    document.getElementById('export-modal').style.display = 'flex';
}

// Update project list when source changes
document.addEventListener('DOMContentLoaded', () => {
    const sourceSelect = document.getElementById('export-source');
    if (sourceSelect) {
        sourceSelect.addEventListener('change', showExportModal);
    }
});

// Hide export modal
function hideExportModal() {
    document.getElementById('export-modal').style.display = 'none';
}

// Do export
async function doExport() {
    const source = document.getElementById('export-source').value;
    const type = document.getElementById('export-type').value;
    const project = document.getElementById('export-project').value;
    const startDate = document.getElementById('export-start-date').value;
    const endDate = document.getElementById('export-end-date').value;

    const dateStr = new Date().toISOString().split('T')[0];

    try {
        hideExportModal();

        // If specific project selected
        if (project) {
            const [projSource, projName] = project.split(':');
            await exportProjectReport(projSource, projName, type, startDate, endDate, dateStr);
            return;
        }

        if (source === 'both') {
            await exportSource('claude', type, startDate, endDate, dateStr);
            await exportSource('opencode', type, startDate, endDate, dateStr);
        } else {
            await exportSource(source, type, startDate, endDate, dateStr);
        }

    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}

// Export single project report
async function exportProjectReport(source, projectName, type, startDate, endDate, dateStr) {
    const body = {
        project_name: projectName,
        start_date: startDate || null,
        end_date: endDate || null
    };

    const endpoint = `/api/export/${source}/project`;
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    let filename;
    if (type === 'raw') {
        filename = `${source}_${projectName.replace(/[^a-zA-Z0-9]/g, '_')}_${dateStr}.json`;
        downloadJSON(data, filename);
    } else {
        // Generate markdown report
        const markdown = generateProjectMarkdown(data, type === 'detailed');
        filename = `${source}_${projectName.replace(/[^a-zA-Z0-9]/g, '_')}_${dateStr}.md`;
        downloadText(markdown, filename, 'text/markdown');
    }
}

// Generate project markdown report
function generateProjectMarkdown(data, includePrompts) {
    const summary = data.summary || {};
    const tokens = summary.total_tokens || {};
    const dailyStats = data.daily_stats || [];
    const prompts = data.prompts || [];

    let md = `# AI 使用数据报告\n\n`;
    md += `**项目**: ${data.project_name || 'All Projects'}\n`;
    md += `**数据源**: ${data.source || 'Unknown'}\n`;
    md += `**开发者**: ${data.developer?.name || 'Unknown'} (${data.developer?.email || 'N/A'})\n`;
    md += `**导出时间**: ${new Date().toLocaleString('zh-CN')}\n\n`;

    if (data.export_info?.date_range) {
        md += `**日期范围**: ${data.export_info.date_range.start || '开始'} ~ ${data.export_info.date_range.end || '结束'}\n\n`;
    }

    md += `---\n\n`;
    md += `## 汇总统计\n\n`;
    md += `| 指标 | 数值 |\n`;
    md += `|------|------|\n`;
    md += `| 总请求 | ${summary.total_requests || 0} |\n`;
    md += `| 总会话 | ${summary.total_sessions || 0} |\n`;
    md += `| 总提示词 | ${summary.total_prompts || 0} |\n`;
    md += `| 输入 Token | ${formatNumber(tokens.input || 0)} |\n`;
    md += `| 输出 Token | ${formatNumber(tokens.output || 0)} |\n`;
    md += `| 缓存创建 Token | ${formatNumber(tokens.cache_creation || 0)} |\n`;
    md += `| 缓存读取 Token | ${formatNumber(tokens.cache_read || 0)} |\n`;
    md += `| 总 Token | ${formatNumber(tokens.total || 0)} |\n`;
    md += `| 估算成本 | $${(summary.total_cost || 0).toFixed(2)} |\n\n`;

    // Daily stats
    if (dailyStats.length > 0) {
        md += `## 每日统计\n\n`;
        md += `| 日期 | 请求 | 会话 | 提示词 | 输入Token | 输出Token |\n`;
        md += `|------|------|------|--------|-----------|----------|\n`;
        dailyStats.forEach(d => {
            md += `| ${d.date} | ${d.requests || 0} | ${d.sessions || 0} | ${d.prompts || 0} | ${formatNumber(d.tokens?.input || 0)} | ${formatNumber(d.tokens?.output || 0)} |\n`;
        });
        md += `\n`;
    }

    // Prompts (if detailed)
    if (includePrompts && prompts.length > 0) {
        md += `## 提示词记录\n\n`;
        md += `共 ${prompts.length} 条提示词\n\n`;

        prompts.forEach((p, i) => {
            md += `### 提示词 ${i + 1}\n\n`;
            md += `- **时间**: ${p.timestamp || 'N/A'}\n`;
            md += `- **会话**: ${p.session_id || 'N/A'}\n`;
            md += `- **模型**: ${p.model || 'N/A'}\n`;
            if (p.tools_used?.length > 0) {
                md += `- **使用工具**: ${p.tools_used.join(', ')}\n`;
            }
            md += `- **Token**: 输入 ${p.tokens_used?.input || 0}, 输出 ${p.tokens_used?.output || 0}\n`;
            if (p.has_error) {
                md += `- **错误**: 是\n`;
            }
            md += `\n**内容**:\n\`\`\`\n${p.prompt || '(空)'}\n\`\`\`\n\n`;
            md += `---\n\n`;
        });
    }

    return md;
}

async function exportSource(source, type, startDate, endDate, dateStr) {
    const body = {
        start_date: startDate || null,
        end_date: endDate || null
    };

    let filename;

    if (type === 'raw') {
        const endpoint = `/api/export/${source}`;
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        filename = `${source}_raw_${dateStr}.json`;
        downloadJSON(data, filename);

    } else {
        // summary or detailed - generate markdown
        const endpoint = `/api/export/${source}`;
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const markdown = generateProjectMarkdown(data, type === 'detailed');
        filename = `${source}_${type}_${dateStr}.md`;
        downloadText(markdown, filename, 'text/markdown');
    }
}

function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function downloadText(text, filename, mimeType) {
    const blob = new Blob([text], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function formatDate(isoString) {
    if (!isoString) return 'N/A';
    try {
        const date = new Date(isoString);
        return date.toLocaleDateString('zh-CN');
    } catch {
        return isoString;
    }
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString();
}
