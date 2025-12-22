// API Base URL
const API_BASE = 'http://localhost:8000/api';

// Token management
let token = localStorage.getItem('admin_token');
let currentUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (token) {
        checkAuth();
    }
});

// Auth functions
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            currentUser = await response.json();
            if (currentUser.is_admin) {
                showDashboard();
            } else {
                alert('Access denied. Admin privileges required.');
                logout();
            }
        } else {
            localStorage.removeItem('admin_token');
            token = null;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('admin_token');
        token = null;
    }
}

async function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    
    if (!username || !password) {
        errorDiv.textContent = 'Please fill in all fields';
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.user.is_admin) {
                token = data.access_token;
                currentUser = data.user;
                localStorage.setItem('admin_token', token);
                showDashboard();
                errorDiv.textContent = '';
            } else {
                errorDiv.textContent = 'Admin privileges required';
            }
        } else {
            errorDiv.textContent = data.detail || 'Login failed';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        console.error('Login error:', error);
    }
}

function logout() {
    localStorage.removeItem('admin_token');
    token = null;
    currentUser = null;
    document.getElementById('authSection').style.display = 'block';
    document.getElementById('adminDashboard').style.display = 'none';
}

function showDashboard() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('adminDashboard').style.display = 'block';
    document.getElementById('adminName').textContent = currentUser.full_name || currentUser.username;
    
    loadStats();
    loadUsers();
}

// Stats functions
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/admin/stats`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const stats = await response.json();
            displayStats(stats);
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function displayStats(stats) {
    const container = document.getElementById('statsGrid');
    container.innerHTML = `
        <div class="stat-card">
            <h3>Total Users</h3>
            <div class="value">${stats.total_users}</div>
        </div>
        <div class="stat-card">
            <h3>Total Buckets</h3>
            <div class="value">${stats.total_buckets}</div>
        </div>
        <div class="stat-card">
            <h3>Total Files</h3>
            <div class="value">${stats.total_files}</div>
        </div>
        <div class="stat-card">
            <h3>Total Storage</h3>
            <div class="value">${stats.total_storage_gb} GB</div>
        </div>
    `;
}

// Users functions
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/admin/users`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayUsers(data.users);
        }
    } catch (error) {
        console.error('Failed to load users:', error);
    }
}

function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem;">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => {
        const usagePercent = user.storage_percentage;
        const usageColor = usagePercent > 90 ? '#ff6b6b' : usagePercent > 70 ? '#ffa500' : '#4ecdc4';
        
        return `
            <tr>
                <td><strong>${user.username}</strong></td>
                <td>${user.email || 'N/A'}</td>
                <td>${user.full_name || 'N/A'}</td>
                <td>
                    <span class="badge ${user.is_admin ? 'badge-admin' : 'badge-user'}">
                        ${user.is_admin ? 'Admin' : 'User'}
                    </span>
                </td>
                <td>${user.storage_used_gb} GB</td>
                <td>${user.storage_limit_gb} GB</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${Math.min(usagePercent, 100)}%; background: ${usageColor};"></div>
                        </div>
                        <span>${usagePercent.toFixed(1)}%</span>
                    </div>
                </td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
            </tr>
        `;
    }).join('');
}

function refreshData() {
    loadStats();
    loadUsers();
}

// Auto-refresh every 30 seconds
setInterval(() => {
    if (token && currentUser && currentUser.is_admin) {
        refreshData();
    }
}, 30000);

