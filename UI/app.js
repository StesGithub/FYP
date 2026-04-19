// Cognito config
const COGNITO_DOMAIN = 'https://eu-west-1hu2tntjq3.auth.eu-west-1.amazoncognito.com';
const CLIENT_ID = '51jji6cvtkpmqvqh3kf8m90b09';
const REDIRECT_URI = 'http://localhost:5500';
const DASHBOARD_URL = 'https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/dashboard';


let allFiles =[];

// Login function this redirects to Cognito hosted UI
function login() {
    const url = `${COGNITO_DOMAIN}/login?client_id=${CLIENT_ID}&response_type=token&scope=email+openid+profile&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`;
    console.log('Login URL:', url);
    window.location.href = url;
}

// Logout function
function logout() {
    localStorage.removeItem('id_token');
    window.location.href = `${COGNITO_DOMAIN}/logout?client_id=${CLIENT_ID}&logout_uri=${REDIRECT_URI}`;
}

// Check if user is logged in on page load
window.onload = async () => {
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    const idToken = params.get('id_token');
    const accessToken = params.get('access_token');

    if (idToken) {
        localStorage.setItem('id_token', idToken);
    }
    if (accessToken) {
        localStorage.setItem('access_token', accessToken);
    }
    if (idToken || accessToken) {
        window.location.hash = '';
    }

    const storedToken = localStorage.getItem('id_token');

    if (storedToken) {
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('appSection').style.display = 'block';
        const payload = JSON.parse(atob(storedToken.split('.')[1]));
        document.getElementById('welcomeMessage').textContent = `Welcome, ${payload.email}`;
    } else {
        document.getElementById('loginSection').style.display = 'block';
        document.getElementById('appSection').style.display = 'none';
    }
};

async function uploadFile() {

    const token = localStorage.getItem('id_token');
    const fileInput = document.getElementById('fileInput');
    const status = document.getElementById('status');
    const file = fileInput.files[0];

    if (!file) {
        status.textContent = 'Please select a file first';
        return;
    }

    status.textContent = 'Uploading...';

    //Convert file to base64
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = async () => {
        const base64File = reader.result.split(',')[1];

        try {
            const response = await fetch('https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token || ''
                },
                body: JSON.stringify({
                    fileName: file.name,
                    file: base64File
                })
            });

            const result = await response.json();

            if (response.ok) {
                status.textContent = '✅ ' + result;
            } else {
                status.textContent = '❌ ' + result;
            }
        } catch (error) {
            status.textContent = '❌ Upload failed: ' + error.message;
        }
    };
}


async function listFiles() {
    const token = localStorage.getItem('id_token');
    console.log(token);
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '<tr><td colspan="3">Loading...</td></tr>';

    try {
        const response = await fetch('https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/listfiles', {
            method: 'GET',
            headers: {
                'Authorization': token || ''
            }
        });

        const raw = await response.json();
        const files = JSON.parse(raw.body);
        allFiles = files;   

        if (files.length === 0) {
            fileList.innerHTML = '<tr><td colspan="3">No files in bucket</td></tr>';
            return;
        }

        renderFileTable(files);

    } catch (error) {
        fileList.innerHTML = `<tr><td colspan="3"> Error: ${error.message}</td></tr>`;
    }
}

function filterFiles(){
    const search = document.getElementById('searchInput').value.toLowerCase();
    const filtered = allFiles.filter(f => f.fileName.toLowerCase().includes(search));
    renderFileTable(filtered);
}

function renderFileTable(files){
    const fileList = document.getElementById('fileList');


    const filtered = files.filter(f => !f.fileName.startsWith('model/'))
    if(filtered.length === 0){

        fileList.innerHTML = '<tr> <td> No files found</td></tr>';
        return;
    }

    fileList.innerHTML = filtered.map(file => `
    <tr>
        <td>${file.fileName}</td>
        <td>${file.size}</td>
        <td>${file.lastModified}</td>
        <td>
            <button onclick="downloadFile('${file.fileName}')" 
                style="background: #001aff; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                Download
            </button>
            <button onclick="deleteFile('${file.fileName}')" 
                style="background: #ff1900; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                Delete
            </button>
        </td>
    </tr>
`).join('');

}

async function downloadFile(fileName) {
    const token = localStorage.getItem('id_token');
    const status = document.getElementById('status');
    status.textContent = `Requesting access for ${fileName}...`;

    try {
        const response = await fetch(`https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/access?fileKey=${encodeURIComponent(fileName)}`, {
            method: 'GET',
            headers: { 'Authorization': token || '' }
        });

        const result = await response.json();

        if (response.ok && result.downloadUrl) {
            status.textContent = `Access granted, Downloading`;
            const a = document.createElement('a');
            a.href = result.downloadUrl;
            a.download = fileName.split('/').pop();
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            status.textContent = `${result.message || 'Access denied'}`;
        }
    } catch (error) {
        status.textContent = `An error occured: ${error.message}`;
    }
}

async function loadDashboard() {

    const token = localStorage.getItem('id_token');
    console.log('Token being sent:', token ? token.substring(0, 50) : 'NULL');
    const status = document.getElementById('status');
    status.textContent = 'Loading dashboard...';

    try {
        const response = await fetch(DASHBOARD_URL, {
            method: 'GET',
            headers: {
                'Authorization': token || ''
            }
        });
        console.log('Status:', response.status);
        const text = await response.text();
        console.log('Raw response:', text);

        const raw = JSON.parse(text);
        const data = typeof raw.body === 'string' ? JSON.parse(raw.body) : raw;

        //Update summary cards
        document.getElementById('total').textContent = data.summary.total;
        document.getElementById('restricted').textContent = data.summary.restricted;
        document.getElementById('internal').textContent = data.summary.internal;
        document.getElementById('public').textContent = data.summary.public;
        document.getElementById('quarantine').textContent = data.summary.quarantine;
        document.getElementById('sklearn').textContent = data.summary.classifiedBySklearn;
        document.getElementById('comprehend').textContent = data.summary.classifiedByComprehend;

        //Update classifications table
        const classBody = document.getElementById('classificationsBody');
        if (data.classifications.length === 0) {
            classBody.innerHTML = '<tr><td colspan="6">No classifications found</td></tr>';
        } else {
            classBody.innerHTML = data.classifications.map(item => `
                <tr>
                    <td>${item.fileKey || '-'}</td>
                    <td><span class="badge ${getBadgeClass(item.accessLevel)}">${item.accessLevel || '-'}</span></td>
                    <td>${item.confidence ? (parseFloat(item.confidence) * 100).toFixed(1) + '%' : '-'}</td>
                    <td><span class="badge ${getModelBadge(item.classifiedBy)}">${item.classifiedBy || '-'}</span></td>
                    <td>${item.uploadTimestamp || '-'}</td>
                    <td>${item.status || '-'}</td>
                    <td>
                        <select id="select-${item.ClassificationId}">
                            <option value="RESTRICTED">RESTRICTED</option>
                            <option value="INTERNAL">INTERNAL</option>
                            <option value="PUBLIC">PUBLIC</option>
                            <option value="QUARANTINE">QUARANTINE</option>
                        </select>
                        <button onclick="reclassifyFile('${item.fileKey}', '${item.ClassificationId}')"
                            style="background: #2c3e50; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; margin-left: 5px;">
                            Reclassify
                        </button>
                    </td>
                </tr>
            `).join('');
        }

        //Update audit log
        const auditBody = document.getElementById('auditBody');
        if (data.auditLog.length === 0) {
            auditBody.innerHTML = '<tr><td colspan="5">No audit logs found</td></tr>';
        } else {
            auditBody.innerHTML = data.auditLog.map(item => `
                <tr>
                    <td>${item.timestamp || '-'}</td>
                    <td>${item.action || '-'}</td>
                    <td>${item.fileKey || '-'}</td>
                    <td><span class="badge ${getBadgeClass(item.accessLevel)}">${item.accessLevel || '-'}</span></td>
                    <td>${item.classifiedBy || '-'}</td>
                </tr>
            `).join('');
        }

        status.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;

    } catch (error) {
        status.textContent = `❌ Error: ${error.message}`;
    }
}

function getBadgeClass(level) {
    const map = {
        'RESTRICTED': 'badge-restricted',
        'INTERNAL': 'badge-internal',
        'PUBLIC': 'badge-public',
        'QUARANTINE': 'badge-quarantine'
    };
    return map[level] || 'badge-quarantine';
}

function getModelBadge(model) {
    return model === 'ML_SKLEARN' ? 'badge-sklearn' : 'badge-comprehend';
}

async function deleteFile(fileName) {
    if (!confirm(`Are you sure you want to permanently delete ${fileName}? This cannot be undone.`)) return;

    const token = localStorage.getItem('id_token');
    const status = document.getElementById('status');
    status.textContent = `Deleting ${fileName}...`;

    try {
        const response = await fetch(`https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/delete?fileKey=${encodeURIComponent(fileName)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token || ''
            }
        });

        const raw = await response.json();
        const result = typeof raw.body === 'string' ? JSON.parse(raw.body) : raw;

        if (response.ok) {
            status.textContent = `${fileName} deleted successfully`;
            listFiles();
        } else {
            status.textContent = `${result.message || 'Delete failed'}`;
        }
    } catch (error) {
        status.textContent = `Delete failed: ${error.message}`;
    }
}


async function reclassifyFile(fileKey, classificationId) {
    const token = localStorage.getItem('id_token');
    const newClassification = document.getElementById(`select-${classificationId}`).value;
    const reason = prompt('Enter reason for reclassification:');

    if (!reason) return;

    try {
        const response = await fetch('https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/reclassify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token || ''
            },
            body: JSON.stringify({
                fileKey: fileKey,
                newClassification: newClassification,
                reason: reason
            })
        });

        const raw = await response.json();
        const result = typeof raw.body === 'string' ? JSON.parse(raw.body) : raw;

        if (response.ok) {
            alert(`✅ ${result.message}`);
            loadDashboard();
        } else {
            alert(`❌ ${result.message || 'Reclassification failed'}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}