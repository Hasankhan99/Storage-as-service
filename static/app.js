// API Base URL
const API_BASE = 'http://localhost:8000/api';

// Token management
let token = localStorage.getItem('token');
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
            showDashboard();
        } else {
            localStorage.removeItem('token');
            token = null;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('token');
        token = null;
    }
}

function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.querySelectorAll('.tab-btn')[0].classList.add('active');
    document.querySelectorAll('.tab-btn')[1].classList.remove('active');
}

function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    document.querySelectorAll('.tab-btn')[0].classList.remove('active');
    document.querySelectorAll('.tab-btn')[1].classList.add('active');
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
            token = data.access_token;
            currentUser = data.user;
            localStorage.setItem('token', token);
            showDashboard();
            errorDiv.textContent = '';
        } else {
            errorDiv.textContent = data.detail || 'Login failed';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        console.error('Login error:', error);
    }
}

async function register() {
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const fullName = document.getElementById('regFullName').value;
    const errorDiv = document.getElementById('registerError');
    
    if (!username || !email || !password) {
        errorDiv.textContent = 'Please fill in all required fields';
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('email', email);
        formData.append('password', password);
        if (fullName) formData.append('full_name', fullName);
        
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            errorDiv.textContent = '';
            errorDiv.className = 'success-message';
            errorDiv.textContent = 'Registration successful! Please login.';
            setTimeout(() => {
                showLogin();
                errorDiv.className = 'error-message';
            }, 2000);
        } else {
            errorDiv.textContent = data.detail || 'Registration failed';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        console.error('Register error:', error);
    }
}

function logout() {
    localStorage.removeItem('token');
    token = null;
    currentUser = null;
    document.getElementById('authSection').style.display = 'block';
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('userInfo').style.display = 'none';
}

function showDashboard() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    document.getElementById('userInfo').style.display = 'flex';
    document.getElementById('userName').textContent = currentUser.full_name || currentUser.username;
    
    updateStorageInfo();
    loadBuckets();
}

// Storage info
async function updateStorageInfo() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const user = await response.json();
            const percentage = (user.storage_used / user.storage_limit) * 100;
            
            document.getElementById('storageBar').style.width = `${Math.min(percentage, 100)}%`;
            document.getElementById('storageText').textContent = 
                `${user.storage_used_gb} GB / ${user.storage_limit_gb} GB used`;
        }
    } catch (error) {
        console.error('Failed to update storage info:', error);
    }
}

// Bucket functions
async function loadBuckets() {
    try {
        const response = await fetch(`${API_BASE}/buckets`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayBuckets(data.buckets);
        }
    } catch (error) {
        console.error('Failed to load buckets:', error);
    }
}

function displayBuckets(buckets) {
    const container = document.getElementById('bucketsList');
    
    if (buckets.length === 0) {
        container.innerHTML = '<p class="loading">No buckets yet. Create your first bucket!</p>';
        return;
    }
    
    container.innerHTML = buckets.map(bucket => `
        <div class="bucket-card" onclick="viewBucket('${bucket.name}')">
            <h3>${bucket.name}</h3>
            <p>${bucket.description || 'No description'}</p>
            <div class="bucket-stats">
                <span>${bucket.file_count} files</span>
                <span>${formatBytes(bucket.total_size)}</span>
            </div>
            <div class="bucket-actions" onclick="event.stopPropagation()">
                <button class="btn btn-danger" onclick="deleteBucket('${bucket.name}')">Delete</button>
            </div>
        </div>
    `).join('');
}

function showCreateBucket() {
    document.getElementById('createBucketModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    if (modalId === 'createBucketModal') {
        document.getElementById('bucketName').value = '';
        document.getElementById('bucketDescription').value = '';
        document.getElementById('bucketError').textContent = '';
    }
}

async function createBucket() {
    const name = document.getElementById('bucketName').value;
    const description = document.getElementById('bucketDescription').value;
    const errorDiv = document.getElementById('bucketError');
    
    if (!name) {
        errorDiv.textContent = 'Bucket name is required';
        return;
    }
    
    try {
        const params = new URLSearchParams({ name });
        if (description) params.append('description', description);
        
        const response = await fetch(`${API_BASE}/buckets?${params}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            closeModal('createBucketModal');
            loadBuckets();
        } else {
            errorDiv.textContent = data.detail || 'Failed to create bucket';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        console.error('Create bucket error:', error);
    }
}

async function viewBucket(bucketName) {
    try {
        const [bucketRes, filesRes] = await Promise.all([
            fetch(`${API_BASE}/buckets/${bucketName}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            }),
            fetch(`${API_BASE}/buckets/${bucketName}/files`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
        ]);
        
        if (bucketRes.ok && filesRes.ok) {
            const bucket = await bucketRes.json();
            const filesData = await filesRes.json();
            
            displayBucketDetails(bucket, filesData.files);
        }
    } catch (error) {
        console.error('Failed to load bucket details:', error);
    }
}

function displayBucketDetails(bucket, files) {
    document.getElementById('bucketDetailsTitle').textContent = bucket.name;
    
    const content = document.getElementById('bucketDetailsContent');
    content.innerHTML = `
        <p><strong>Description:</strong> ${bucket.description || 'No description'}</p>
        <p><strong>Files:</strong> ${bucket.file_count}</p>
        <p><strong>Total Size:</strong> ${formatBytes(bucket.total_size)}</p>
        
        <div class="file-upload-area" onclick="document.getElementById('fileInput').click()">
            <input type="file" id="fileInput" onchange="uploadFile('${bucket.name}')">
            <label class="file-upload-label">📁 Click to upload file</label>
        </div>
        
        <div class="files-list">
            <h3>Files (${files.length})</h3>
            ${files.length === 0 ? '<p>No files yet</p>' : files.map(file => `
                <div class="file-item">
                    <div class="file-info">
                        <div class="file-name">${file.filename}</div>
                        <div class="file-meta">
                            ${formatBytes(file.size)} • ${file.content_type} • ${new Date(file.uploaded_at).toLocaleDateString()}
                        </div>
                    </div>
                    <div class="file-actions">
                        <button class="btn btn-success" onclick="downloadFile('${bucket.name}', '${file.filename}')">Download</button>
                        <button class="btn btn-danger" onclick="deleteFile('${bucket.name}', '${file.filename}')">Delete</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    document.getElementById('bucketDetailsModal').style.display = 'block';
}

async function uploadFile(bucketName) {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/buckets/${bucketName}/files`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            viewBucket(bucketName);
            updateStorageInfo();
        } else {
            alert(data.detail || 'Failed to upload file');
        }
    } catch (error) {
        alert('Network error. Please try again.');
        console.error('Upload error:', error);
    }
}

async function downloadFile(bucketName, filename) {
    try {
        const response = await fetch(`${API_BASE}/buckets/${bucketName}/files/${filename}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            window.URL.revokeObjectURL(url);
        } else {
            alert('Failed to download file');
        }
    } catch (error) {
        alert('Network error. Please try again.');
        console.error('Download error:', error);
    }
}

async function deleteFile(bucketName, filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/buckets/${bucketName}/files/${filename}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            viewBucket(bucketName);
            updateStorageInfo();
        } else {
            alert('Failed to delete file');
        }
    } catch (error) {
        alert('Network error. Please try again.');
        console.error('Delete file error:', error);
    }
}

async function deleteBucket(bucketName) {
    if (!confirm(`Are you sure you want to delete bucket "${bucketName}"? This will delete all files in it.`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/buckets/${bucketName}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            loadBuckets();
            updateStorageInfo();
        } else {
            alert('Failed to delete bucket');
        }
    } catch (error) {
        alert('Network error. Please try again.');
        console.error('Delete bucket error:', error);
    }
}

// Utility functions
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

