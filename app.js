// Cognito config
const COGNITO_DOMAIN = 'https://eu-west-1hu2tntjq3.auth.eu-west-1.amazoncognito.com';
const CLIENT_ID = '51jji6cvtkpmqvqh3kf8m90b09';
const REDIRECT_URI = 'http://localhost:5500';

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
    // Check for token in URL hash
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    const token = params.get('id_token');
    
    if (token) {
        localStorage.setItem('id_token', token);
        window.location.hash = ''; // Clean URL
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
    const fileInput = document.getElementById('fileInput');
    const status = document.getElementById('status');
    const file = fileInput.files[0];

    if (!file) {
        status.textContent = 'Please select a file first!';
        return;
    }

    status.textContent = 'Uploading...';

    // Convert file to base64
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = async () => {
        const base64File = reader.result.split(',')[1];

        try { 
            const response = await fetch('https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
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
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '<tr><td colspan="3">Loading...</td></tr>';

    try {
        const response = await fetch('https://s6gly9n709.execute-api.eu-west-1.amazonaws.com/dev/listfiles', {
            method: 'GET'
        });

        const raw = await response.json();
        const files = JSON.parse(raw.body);

        if (files.length === 0) {
            fileList.innerHTML = '<tr><td colspan="3">No files in bucket</td></tr>';
            return;
        }

        fileList.innerHTML = files.map(file => `
    <tr>
        <td>${file.fileName}</td>
        <td>${file.size}</td>
        <td>${file.lastModified}</td>
    </tr>
`).join('');

    } catch (error) {
        fileList.innerHTML = `<tr><td colspan="3">❌ Error: ${error.message}</td></tr>`;
    }
}