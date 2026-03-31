// Admin Dashboard JavaScript

const API_BASE = '/api/admin';
let currentUser = null;
let currentPage = { users: 1, shares: 1 };

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Check if on users page
    if (document.getElementById('users-tbody')) {
        loadUsers(1);
    }
    // Check if on shares page
    if (document.getElementById('shares-tbody')) {
        loadShares(1);
    }
});

// Modal functions
function showModal(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

// Close modal on overlay click
document.getElementById('modal-overlay')?.addEventListener('click', function(e) {
    if (e.target === this) {
        closeModal();
    }
});

// Load users
async function loadUsers(page = 1) {
    currentPage.users = page;
    const tbody = document.getElementById('users-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading-state">加载中...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/users?page=${page}&limit=20`);
        if (!response.ok) throw new Error('Failed to load users');

        const data = await response.json();
        renderUsers(data);
        renderPagination('users-pagination', data.total, data.page, data.limit, currentPage.users);
    } catch (error) {
        console.error('Error loading users:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">加载失败</td></tr>';
    }
}

function renderUsers(data) {
    const tbody = document.getElementById('users-tbody');

    if (data.users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无用户</td></tr>';
        return;
    }

    tbody.innerHTML = data.users.map(user => `
        <tr>
            <td>${escapeHtml(user.username)}</td>
            <td>${new Date(user.created_at).toLocaleString('zh-CN')}</td>
            <td>
                ${user.is_active
                    ? '<span class="badge badge-success">启用</span>'
                    : '<span class="badge badge-secondary">禁用</span>'}
            </td>
            <td>${user.share_count}</td>
            <td>
                <button class="btn btn-sm btn-link" onclick="showEditUserModal('${escapeHtml(user.username)}', ${user.is_active})">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteUser('${escapeHtml(user.username)}')">删除</button>
            </td>
        </tr>
    `).join('');
}

// Create user modal
function showCreateUserModal() {
    const content = `
        <form id="create-user-form">
            <div class="form-group">
                <label for="new-username">用户名</label>
                <input type="text" id="new-username" name="username" required minlength="1" maxlength="50">
            </div>
            <div class="form-group">
                <label for="new-password">密码</label>
                <input type="password" id="new-password" name="password" required minlength="8">
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="new-is-active" name="is_active" checked>
                <label for="new-is-active">启用账号</label>
            </div>
            <div class="modal-actions">
                <button type="button" class="btn" onclick="closeModal()">取消</button>
                <button type="submit" class="btn btn-primary">创建</button>
            </div>
        </form>
    `;

    showModal('创建用户', content);

    document.getElementById('create-user-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = {
            username: formData.get('username'),
            password: formData.get('password'),
            is_active: formData.get('is_active') === 'on'
        };

        try {
            const response = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '创建失败');
            }

            closeModal();
            loadUsers(currentPage.users);
        } catch (error) {
            alert('错误: ' + error.message);
        }
    });
}

// Edit user modal
async function showEditUserModal(username, isActive) {
    const content = `
        <form id="edit-user-form">
            <div class="form-group">
                <label>用户名</label>
                <p>${escapeHtml(username)}</p>
            </div>
            <div class="form-group">
                <label for="edit-password">新密码 (留空则不修改)</label>
                <input type="password" id="edit-password" name="password" minlength="8">
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="edit-is-active" name="is_active" ${isActive ? 'checked' : ''}>
                <label for="edit-is-active">启用账号</label>
            </div>
            <div class="modal-actions">
                <button type="button" class="btn" onclick="closeModal()">取消</button>
                <button type="submit" class="btn btn-primary">保存</button>
            </div>
        </form>
    `;

    showModal('编辑用户', content);

    document.getElementById('edit-user-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = {};

        const password = formData.get('password');
        if (password) data.password = password;

        const isActive = formData.get('is_active') === 'on';
        data.is_active = isActive;

        try {
            const response = await fetch(`${API_BASE}/users/${username}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '更新失败');
            }

            closeModal();
            loadUsers(currentPage.users);
        } catch (error) {
            alert('错误: ' + error.message);
        }
    });
}

// Delete user
async function deleteUser(username) {
    if (!confirm(`确定要删除用户 "${username}" 吗？`)) return;

    try {
        const response = await fetch(`${API_BASE}/users/${username}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '删除失败');
        }

        loadUsers(currentPage.users);
    } catch (error) {
        alert('错误: ' + error.message);
    }
}

// Load shares
async function loadShares(page = 1) {
    currentPage.shares = page;
    const tbody = document.getElementById('shares-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading-state">加载中...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/shares?page=${page}&limit=20`);
        if (!response.ok) throw new Error('Failed to load shares');

        const data = await response.json();
        renderShares(data);
        renderPagination('shares-pagination', data.total, data.page, data.limit, currentPage.shares);
    } catch (error) {
        console.error('Error loading shares:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">加载失败</td></tr>';
    }
}

function renderShares(data) {
    const tbody = document.getElementById('shares-tbody');

    if (data.shares.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无分享</td></tr>';
        return;
    }

    tbody.innerHTML = data.shares.map(share => `
        <tr>
            <td>${escapeHtml(share.project_name)}</td>
            <td>${escapeHtml(share.created_by)}</td>
            <td>${new Date(share.created_at).toLocaleString('zh-CN')}</td>
            <td>
                ${share.is_public
                    ? '<span class="badge badge-success">公开</span>'
                    : '<span class="badge badge-secondary">私有</span>'}
            </td>
            <td>
                <a href="/share/${share.id}" class="btn btn-sm btn-link" target="_blank">查看</a>
                <button class="btn btn-sm btn-danger" onclick="deleteShare('${share.id}')">删除</button>
            </td>
        </tr>
    `).join('');
}

// Delete share
async function deleteShare(shareId) {
    if (!confirm('确定要删除此分享吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/shares/${shareId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '删除失败');
        }

        loadShares(currentPage.shares);
    } catch (error) {
        alert('错误: ' + error.message);
    }
}

// Pagination
function renderPagination(containerId, total, page, limit, currentPage) {
    const container = document.getElementById(containerId);
    const totalPages = Math.ceil(total / limit);

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = `
        <button ${page === 1 ? 'disabled' : ''} onclick="${containerId.replace('-pagination', '')}Page(${page - 1})">
            上一页
        </button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        if (i === page || (i <= 3) || (i > totalPages - 3) || (Math.abs(i - page) <= 1)) {
            html += `<button class="${i === page ? 'active' : ''}" onclick="${containerId.replace('-pagination', '')}Page(${i})">${i}</button>`;
        } else if (i === 4 || i === totalPages - 3) {
            html += '<button disabled>...</button>';
        }
    }

    html += `
        <button ${page === totalPages ? 'disabled' : ''} onclick="${containerId.replace('-pagination', '')}Page(${page + 1})">
            下一页
        </button>
    `;

    container.innerHTML = html;
}

// Pagination helpers
function usersPage(page) {
    loadUsers(page);
}

function sharesPage(page) {
    loadShares(page);
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
