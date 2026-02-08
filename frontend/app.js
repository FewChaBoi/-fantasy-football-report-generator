/**
 * Fantasy Football Report Generator - Frontend JavaScript
 */

// DOM Elements
const platformSection = document.getElementById('platform-section');
const yahooAuthSection = document.getElementById('yahoo-auth-section');
const sleeperAuthSection = document.getElementById('sleeper-auth-section');
const mainSection = document.getElementById('main-section');
const progressSection = document.getElementById('progress-section');
const downloadSection = document.getElementById('download-section');
const errorSection = document.getElementById('error-section');

const yahooPlatformBtn = document.getElementById('yahoo-platform-btn');
const sleeperPlatformBtn = document.getElementById('sleeper-platform-btn');
const yahooBackBtn = document.getElementById('yahoo-back-btn');
const sleeperBackBtn = document.getElementById('sleeper-back-btn');

const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const generateBtn = document.getElementById('generate-btn');
const downloadBtn = document.getElementById('download-btn');
const newReportBtn = document.getElementById('new-report-btn');
const retryBtn = document.getElementById('retry-btn');

const sleeperUsernameInput = document.getElementById('sleeper-username');
const sleeperConnectBtn = document.getElementById('sleeper-connect-btn');
const sleeperError = document.getElementById('sleeper-error');

const leagueSelect = document.getElementById('league-select');
const leagueKeyInput = document.getElementById('league-key');
const leagueKeyGroup = document.getElementById('league-key-group');
const sleeperLeagueIdInput = document.getElementById('sleeper-league-id');
const sleeperLeagueIdGroup = document.getElementById('sleeper-league-id-group');
const startYearSelect = document.getElementById('start-year');
const endYearSelect = document.getElementById('end-year');
const statusBadge = document.getElementById('status-badge');

const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const progressMessage = document.getElementById('progress-message');
const errorMessage = document.getElementById('error-message');

const helpLink = document.getElementById('help-link');
const helpModal = document.getElementById('help-modal');
const modalClose = document.querySelector('.modal-close');

// State
let currentJobId = null;
let pollInterval = null;
let currentPlatform = null; // 'yahoo' or 'sleeper'

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    setupEventListeners();
    checkUrlParams();
    populateYearSelects();
});

// Populate year dropdown options
function populateYearSelects() {
    const currentYear = new Date().getFullYear();
    const startYear = 2006; // Yahoo Fantasy started around this time

    for (let year = currentYear; year >= startYear; year--) {
        const option1 = document.createElement('option');
        option1.value = year;
        option1.textContent = year;
        startYearSelect.appendChild(option1);

        const option2 = document.createElement('option');
        option2.value = year;
        option2.textContent = year;
        endYearSelect.appendChild(option2);
    }
}

// Event Listeners
function setupEventListeners() {
    // Platform selection
    yahooPlatformBtn.addEventListener('click', () => {
        showYahooAuthSection();
    });

    sleeperPlatformBtn.addEventListener('click', () => {
        showSleeperAuthSection();
    });

    // Back buttons
    yahooBackBtn.addEventListener('click', () => {
        showPlatformSection();
    });

    sleeperBackBtn.addEventListener('click', () => {
        showPlatformSection();
    });

    // Yahoo login
    loginBtn.addEventListener('click', () => {
        window.location.href = '/auth/login';
    });

    // Sleeper connect
    sleeperConnectBtn.addEventListener('click', connectSleeper);
    sleeperUsernameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            connectSleeper();
        }
    });

    logoutBtn.addEventListener('click', logout);
    generateBtn.addEventListener('click', startGeneration);
    newReportBtn.addEventListener('click', resetToMain);
    retryBtn.addEventListener('click', resetToMain);

    leagueSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            if (currentPlatform === 'sleeper') {
                sleeperLeagueIdInput.value = e.target.value;
            } else {
                leagueKeyInput.value = e.target.value;
            }
        }
    });

    helpLink.addEventListener('click', (e) => {
        e.preventDefault();
        helpModal.classList.remove('hidden');
    });

    modalClose.addEventListener('click', () => {
        helpModal.classList.add('hidden');
    });

    helpModal.addEventListener('click', (e) => {
        if (e.target === helpModal) {
            helpModal.classList.add('hidden');
        }
    });
}

// Check URL parameters for errors/success
function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);

    if (params.has('error')) {
        showError(`Authentication failed: ${params.get('error')}`);
        // Clean URL
        window.history.replaceState({}, '', '/');
    }

    if (params.has('authenticated')) {
        // Clean URL
        window.history.replaceState({}, '', '/');
    }
}

// Authentication
async function checkAuthStatus() {
    try {
        const response = await fetch('/auth/status');
        const data = await response.json();

        if (data.authenticated) {
            currentPlatform = data.platform;
            showMainSection();

            // Update UI based on platform
            if (currentPlatform === 'sleeper') {
                statusBadge.textContent = `Connected to Sleeper (${data.username})`;
                leagueKeyGroup.classList.add('hidden');
                sleeperLeagueIdGroup.classList.remove('hidden');
                document.querySelector('.divider').classList.add('hidden');
                loadSleeperLeagues();
            } else {
                statusBadge.textContent = 'Connected to Yahoo';
                leagueKeyGroup.classList.remove('hidden');
                sleeperLeagueIdGroup.classList.add('hidden');
                document.querySelector('.divider').classList.remove('hidden');
                loadUserLeagues();
            }
        } else {
            showPlatformSection();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showPlatformSection();
    }
}

// Connect to Sleeper
async function connectSleeper() {
    const username = sleeperUsernameInput.value.trim();

    if (!username) {
        showSleeperError('Please enter your Sleeper username');
        return;
    }

    sleeperConnectBtn.disabled = true;
    sleeperConnectBtn.textContent = 'Connecting...';
    hideSleeperError();

    try {
        const response = await fetch('/auth/sleeper/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to connect');
        }

        const data = await response.json();

        if (data.success) {
            currentPlatform = 'sleeper';
            showMainSection();
            statusBadge.textContent = `Connected to Sleeper (${data.user.username})`;
            leagueKeyGroup.classList.add('hidden');
            sleeperLeagueIdGroup.classList.remove('hidden');
            document.querySelector('.divider').classList.add('hidden');
            loadSleeperLeagues();
        }
    } catch (error) {
        console.error('Sleeper connect failed:', error);
        showSleeperError(error.message);
    } finally {
        sleeperConnectBtn.disabled = false;
        sleeperConnectBtn.innerHTML = '<span class="btn-icon">🔗</span> Connect to Sleeper';
    }
}

function showSleeperError(message) {
    sleeperError.textContent = message;
    sleeperError.classList.remove('hidden');
}

function hideSleeperError() {
    sleeperError.classList.add('hidden');
}

// Load Sleeper leagues
async function loadSleeperLeagues() {
    leagueSelect.innerHTML = '<option value="">Loading your leagues...</option>';

    try {
        const response = await fetch('/api/sleeper/leagues');

        if (!response.ok) {
            throw new Error('Failed to load leagues');
        }

        const data = await response.json();

        if (data.leagues && data.leagues.length > 0) {
            leagueSelect.innerHTML = '<option value="">Select a league...</option>';

            // Group leagues by name, keeping the most recent year's ID
            const leaguesByName = {};
            data.leagues.forEach(league => {
                const name = league.name;
                if (!leaguesByName[name] || league.year > leaguesByName[name].year) {
                    leaguesByName[name] = league;
                }
            });

            // Sort by name and add to dropdown
            Object.values(leaguesByName)
                .sort((a, b) => a.name.localeCompare(b.name))
                .forEach(league => {
                    const option = document.createElement('option');
                    option.value = league.league_id;
                    option.textContent = league.name;
                    leagueSelect.appendChild(option);
                });
        } else {
            leagueSelect.innerHTML = '<option value="">No leagues found - enter ID manually</option>';
        }
    } catch (error) {
        console.error('Failed to load Sleeper leagues:', error);
        leagueSelect.innerHTML = '<option value="">Could not load leagues - enter ID manually</option>';
    }
}

async function logout() {
    try {
        await fetch('/auth/logout', { method: 'POST' });
        showAuthSection();
    } catch (error) {
        console.error('Logout failed:', error);
    }
}

// Load user's leagues
async function loadUserLeagues() {
    leagueSelect.innerHTML = '<option value="">Loading your leagues...</option>';

    try {
        const response = await fetch('/api/leagues');

        if (!response.ok) {
            throw new Error('Failed to load leagues');
        }

        const data = await response.json();

        if (data.leagues && data.leagues.length > 0) {
            leagueSelect.innerHTML = '<option value="">Select a league...</option>';

            // Group leagues by name, keeping the most recent year's key
            const leaguesByName = {};
            data.leagues.forEach(league => {
                const name = league.name;
                if (!leaguesByName[name] || league.year > leaguesByName[name].year) {
                    leaguesByName[name] = league;
                }
            });

            // Sort by name and add to dropdown
            Object.values(leaguesByName)
                .sort((a, b) => a.name.localeCompare(b.name))
                .forEach(league => {
                    const option = document.createElement('option');
                    option.value = league.league_key;
                    option.textContent = league.name;
                    leagueSelect.appendChild(option);
                });
        } else {
            leagueSelect.innerHTML = '<option value="">No leagues found - enter key manually</option>';
        }
    } catch (error) {
        console.error('Failed to load leagues:', error);
        leagueSelect.innerHTML = '<option value="">Could not load leagues - enter key manually</option>';
    }
}

// Report Generation
async function startGeneration() {
    let leagueIdentifier;
    let apiEndpoint;
    let requestBody;

    if (currentPlatform === 'sleeper') {
        leagueIdentifier = sleeperLeagueIdInput.value.trim();

        if (!leagueIdentifier) {
            alert('Please enter a league ID or select a league');
            return;
        }

        apiEndpoint = '/api/sleeper/report/generate';
        requestBody = { league_id: leagueIdentifier };
    } else {
        leagueIdentifier = leagueKeyInput.value.trim();

        if (!leagueIdentifier) {
            alert('Please enter a league key or select a league');
            return;
        }

        // Validate Yahoo format
        const parts = leagueIdentifier.split('.');
        if (parts.length !== 3 || parts[1] !== 'l') {
            alert('Invalid league key format. Expected format: 461.l.333910');
            return;
        }

        apiEndpoint = '/api/report/generate';
        requestBody = { league_key: leagueIdentifier };
    }

    // Get year range
    const startYear = startYearSelect.value ? parseInt(startYearSelect.value) : null;
    const endYear = endYearSelect.value ? parseInt(endYearSelect.value) : null;

    // Validate year range
    if (startYear && endYear && startYear > endYear) {
        alert('Start year must be before or equal to end year');
        return;
    }

    if (startYear) requestBody.start_year = startYear;
    if (endYear) requestBody.end_year = endYear;

    showProgressSection();

    try {
        const response = await fetch(apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start report generation');
        }

        const data = await response.json();
        currentJobId = data.job_id;

        // Start polling for status
        pollInterval = setInterval(pollJobStatus, 1000);

    } catch (error) {
        console.error('Generation failed:', error);
        showError(error.message);
    }
}

async function pollJobStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/report/status/${currentJobId}`);
        const job = await response.json();

        updateProgress(job.progress, job.message);

        if (job.status === 'completed') {
            clearInterval(pollInterval);
            downloadBtn.href = job.download_url;
            showDownloadSection();
        } else if (job.status === 'failed') {
            clearInterval(pollInterval);
            showError(job.error || 'Report generation failed');
        }

    } catch (error) {
        console.error('Status poll failed:', error);
    }
}

function updateProgress(percent, message) {
    progressFill.style.width = `${percent}%`;
    progressText.textContent = `${percent}%`;
    progressMessage.textContent = message;
}

// UI State Management
function showPlatformSection() {
    platformSection.classList.remove('hidden');
    yahooAuthSection.classList.add('hidden');
    sleeperAuthSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

function showYahooAuthSection() {
    platformSection.classList.add('hidden');
    yahooAuthSection.classList.remove('hidden');
    sleeperAuthSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

function showSleeperAuthSection() {
    platformSection.classList.add('hidden');
    yahooAuthSection.classList.add('hidden');
    sleeperAuthSection.classList.remove('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    sleeperUsernameInput.value = '';
    hideSleeperError();
}

function showMainSection() {
    platformSection.classList.add('hidden');
    yahooAuthSection.classList.add('hidden');
    sleeperAuthSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

function showProgressSection() {
    platformSection.classList.add('hidden');
    yahooAuthSection.classList.add('hidden');
    sleeperAuthSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');

    // Reset progress
    updateProgress(0, 'Starting...');
}

function showDownloadSection() {
    platformSection.classList.add('hidden');
    yahooAuthSection.classList.add('hidden');
    sleeperAuthSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.remove('hidden');
    errorSection.classList.add('hidden');
}

function showError(message) {
    platformSection.classList.add('hidden');
    yahooAuthSection.classList.add('hidden');
    sleeperAuthSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.remove('hidden');

    errorMessage.textContent = message;
}

function resetToMain() {
    currentJobId = null;
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    showMainSection();
}
