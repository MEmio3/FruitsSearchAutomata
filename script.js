// Global state
let selectedProfiles = [];
let availableProfiles = [];
let isRunning = false;
let statusPoller = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateFruitCount();
    loadProfilesIfChrome();
    
    // Add event listener for fruit list changes
    document.getElementById('fruitList').addEventListener('input', updateFruitCount);
});

// Update fruit count
function updateFruitCount() {
    const fruitList = document.getElementById('fruitList').value.trim();
    const fruits = fruitList.split('\n').filter(f => f.trim());
    document.getElementById('fruitCount').textContent = fruits.length;
}

// Browser change handler
function onBrowserChange() {
    const browser = document.getElementById('browserSelect').value;
    const profileSection = document.getElementById('profileSection');
    
    if (browser === 'chrome') {
        profileSection.style.display = 'block';
        loadProfilesIfChrome();
    } else {
        profileSection.style.display = 'none';
        selectedProfiles = [];
        updateSelectedProfilesDisplay();
    }
}

// Load Chrome profiles
async function loadProfilesIfChrome() {
    const browser = document.getElementById('browserSelect').value;
    if (browser !== 'chrome') return;
    
    try {
        const response = await fetch('/api/profiles');
        const data = await response.json();
        
        availableProfiles = data.profiles;
        const profileInfo = document.getElementById('profileInfo');
        
        if (availableProfiles.length > 0) {
            profileInfo.textContent = `Found ${availableProfiles.length} Chrome profiles`;
            profileInfo.style.color = '#86efac';
        } else {
            profileInfo.textContent = 'No Chrome profiles found';
            profileInfo.style.color = '#fca5a5';
        }
    } catch (error) {
        console.error('Error loading profiles:', error);
        document.getElementById('profileInfo').textContent = 'Error loading profiles';
    }
}

// Open profile selection modal
function openProfileModal() {
    const modal = document.getElementById('profileModal');
    const profileList = document.getElementById('profileList');
    
    // Clear existing content
    profileList.innerHTML = '';
    
    // Populate profiles
    availableProfiles.forEach(profile => {
        const profileItem = document.createElement('div');
        profileItem.className = 'profile-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'profile-checkbox';
        checkbox.id = `profile_${profile.directory}`;
        checkbox.value = JSON.stringify(profile);
        
        // Check if already selected
        if (selectedProfiles.find(p => p.directory === profile.directory)) {
            checkbox.checked = true;
        }
        
        const infoDiv = document.createElement('div');
        infoDiv.className = 'profile-info-item';
        
        const nameDiv = document.createElement('div');
        nameDiv.className = 'profile-name';
        nameDiv.textContent = `📁 ${profile.name}`;
        
        const dirDiv = document.createElement('div');
        dirDiv.className = 'profile-dir';
        dirDiv.textContent = `Directory: ${profile.directory}`;
        
        infoDiv.appendChild(nameDiv);
        infoDiv.appendChild(dirDiv);
        
        profileItem.appendChild(checkbox);
        profileItem.appendChild(infoDiv);
        
        // Add click handler for the entire item
        profileItem.addEventListener('click', (e) => {
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
            }
        });
        
        profileList.appendChild(profileItem);
    });
    
    // Update modal info
    document.getElementById('modalInfo').textContent = 
        `Found ${availableProfiles.length} Chrome profiles. Select the ones you want to use:`;
    
    modal.classList.add('active');
}

// Close profile modal
function closeProfileModal() {
    document.getElementById('profileModal').classList.remove('active');
}

// Select all profiles
function selectAllProfiles() {
    const checkboxes = document.querySelectorAll('.profile-checkbox');
    checkboxes.forEach(cb => cb.checked = true);
}

// Clear all profile selections
function clearAllProfiles() {
    const checkboxes = document.querySelectorAll('.profile-checkbox');
    checkboxes.forEach(cb => cb.checked = false);
}

// Apply profile selection
function applyProfileSelection() {
    selectedProfiles = [];
    const checkboxes = document.querySelectorAll('.profile-checkbox:checked');
    
    checkboxes.forEach(cb => {
        const profile = JSON.parse(cb.value);
        selectedProfiles.push(profile);
    });
    
    updateSelectedProfilesDisplay();
    closeProfileModal();
    
    // Show confirmation
    if (selectedProfiles.length > 0) {
        showNotification(`✅ Selected ${selectedProfiles.length} profile(s) for automation`, 'success');
    }
}

// Update selected profiles display
function updateSelectedProfilesDisplay() {
    const display = document.getElementById('selectedProfilesDisplay');
    
    if (selectedProfiles.length === 0) {
        display.textContent = 'No profiles selected';
        display.style.background = 'rgba(239, 68, 68, 0.1)';
        display.style.borderColor = 'rgba(239, 68, 68, 0.2)';
        display.style.color = '#fca5a5';
    } else {
        const profileNames = selectedProfiles.map(p => p.name);
        let displayText = `✅ Selected: ${profileNames.slice(0, 2).join(', ')}`;
        if (profileNames.length > 2) {
            displayText += ` +${profileNames.length - 2} more`;
        }
        display.textContent = displayText;
        display.style.background = 'rgba(16, 185, 129, 0.1)';
        display.style.borderColor = 'rgba(16, 185, 129, 0.2)';
        display.style.color = '#86efac';
    }
}

// Load default fruits
function loadDefaultFruits() {
    const defaultFruits = [
        "Apple", "Banana", "Orange", "Mango", "Strawberry",
        "Pineapple", "Watermelon", "Grapes", "Kiwi", "Peach",
        "Pear", "Cherry", "Plum", "Apricot", "Coconut",
        "Papaya", "Guava", "Pomegranate", "Lychee", "Dragon Fruit"
    ];
    
    document.getElementById('fruitList').value = defaultFruits.join('\n');
    updateFruitCount();
    showNotification('✅ Default fruits loaded', 'success');
}

// Save fruits to file
async function saveFruits() {
    const fruitList = document.getElementById('fruitList').value.trim();
    const fruits = fruitList.split('\n').filter(f => f.trim());
    
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fruits })
        });
        
        const data = await response.json();
        showNotification(data.message, 'success');
    } catch (error) {
        showNotification('❌ Error saving fruits', 'error');
    }
}

// Load fruits from file
async function loadFruits() {
    try {
        const response = await fetch('/api/load');
        const data = await response.json();
        
        if (data.fruits && data.fruits.length > 0) {
            document.getElementById('fruitList').value = data.fruits.join('\n');
            updateFruitCount();
            showNotification(`📂 Loaded ${data.fruits.length} fruits`, 'success');
        } else {
            showNotification('No saved fruits found', 'warning');
        }
    } catch (error) {
        showNotification('❌ Error loading fruits', 'error');
    }
}

// Start automation
async function startAutomation() {
    const fruitList = document.getElementById('fruitList').value.trim();
    const fruits = fruitList.split('\n').filter(f => f.trim());
    
    if (fruits.length === 0) {
        showNotification('⚠️ Please enter some fruits first!', 'warning');
        return;
    }
    
    const delay = parseFloat(document.getElementById('delayInput').value);
    const browser = document.getElementById('browserSelect').value;
    
    if (delay < 0.5) {
        showNotification('⚠️ Delay must be at least 0.5 seconds', 'warning');
        return;
    }
    
    // Check Chrome profile selection
    if (browser === 'chrome' && selectedProfiles.length === 0) {
        const useDefault = confirm('No Chrome profiles selected. Do you want to use the default profile?');
        if (!useDefault) {
            showNotification('Please select Chrome profiles first', 'warning');
            return;
        }
    }
    
    // Prepare confirmation message
    let confirmMessage = `Ready to start automation:\n\n`;
    confirmMessage += `🌐 Browser: ${browser}`;
    
    if (browser === 'chrome' && selectedProfiles.length > 0) {
        confirmMessage += ` (${selectedProfiles.length} profiles)`;
    }
    
    confirmMessage += `\n🍎 Fruits: ${fruits.length} items`;
    confirmMessage += `\n⏱️ Delay: ${delay} seconds`;
    confirmMessage += `\n\n⚠️ Move mouse to TOP-LEFT corner for emergency stop`;
    confirmMessage += `\n\nContinue?`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fruits,
                delay,
                browser,
                selectedProfiles: browser === 'chrome' ? selectedProfiles : []
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            isRunning = true;
            updateUIState(true);
            startStatusPolling();
            showNotification('🚀 Automation started!', 'success');
        } else {
            showNotification(`❌ ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification('❌ Error starting automation', 'error');
    }
}

// Stop automation
async function stopAutomation() {
    try {
        const response = await fetch('/api/stop', {
            method: 'POST'
        });
        
        if (response.ok) {
            isRunning = false;
            updateUIState(false);
            stopStatusPolling();
            showNotification('⏹️ Automation stopped', 'warning');
        }
    } catch (error) {
        showNotification('❌ Error stopping automation', 'error');
    }
}

// Update UI state
function updateUIState(running) {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusIndicator = document.getElementById('statusIndicator');
    
    if (running) {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        statusIndicator.style.background = '#f59e0b';
        statusIndicator.style.animation = 'pulse 1s infinite';
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        statusIndicator.style.background = '#10b981';
        statusIndicator.style.animation = 'pulse 2s infinite';
    }
}

// Start status polling
function startStatusPolling() {
    statusPoller = setInterval(async () => {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            
            updateStatus(status);
            
            if (!status.is_running && isRunning) {
                isRunning = false;
                updateUIState(false);
                stopStatusPolling();
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 500);
}

// Stop status polling
function stopStatusPolling() {
    if (statusPoller) {
        clearInterval(statusPoller);
        statusPoller = null;
    }
}

// Update status display
function updateStatus(status) {
    document.getElementById('statusMessage').textContent = `🔍 ${status.status}`;
    document.getElementById('currentSearch').textContent = status.current_search || '';
    
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    progressBar.style.width = `${status.progress}%`;
    progressText.textContent = `${Math.round(status.progress)}%`;
}

// Show notification
function showNotification(message, type) {
    // Create a simple notification (you can enhance this with a toast library)
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? 'rgba(16, 185, 129, 0.9)' : 
                      type === 'error' ? 'rgba(239, 68, 68, 0.9)' : 
                      'rgba(245, 158, 11, 0.9)'};
        color: white;
        border-radius: 10px;
        font-weight: 600;
        z-index: 2000;
        animation: slideInRight 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add slide animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);