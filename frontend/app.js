/**
 * Fantasy Football Report Generator - Frontend JavaScript
 */

// DOM Elements
const authSection = document.getElementById('auth-section');
const mainSection = document.getElementById('main-section');
const progressSection = document.getElementById('progress-section');
const downloadSection = document.getElementById('download-section');
const errorSection = document.getElementById('error-section');

const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const generateBtn = document.getElementById('generate-btn');
const downloadBtn = document.getElementById('download-btn');
const newReportBtn = document.getElementById('new-report-btn');
const retryBtn = document.getElementById('retry-btn');

const leagueSelect = document.getElementById('league-select');
const leagueKeyInput = document.getElementById('league-key');
const startYearSelect = document.getElementById('start-year');
const endYearSelect = document.getElementById('end-year');

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
    loginBtn.addEventListener('click', () => {
        window.location.href = '/auth/login';
    });

    logoutBtn.addEventListener('click', logout);
    generateBtn.addEventListener('click', startGeneration);
    newReportBtn.addEventListener('click', resetToMain);
    retryBtn.addEventListener('click', resetToMain);

    leagueSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            leagueKeyInput.value = e.target.value;
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
            showMainSection();
            loadUserLeagues();
        } else {
            showAuthSection();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showAuthSection();
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
    const leagueKey = leagueKeyInput.value.trim();

    if (!leagueKey) {
        alert('Please enter a league key or select a league');
        return;
    }

    // Validate format
    const parts = leagueKey.split('.');
    if (parts.length !== 3 || parts[1] !== 'l') {
        alert('Invalid league key format. Expected format: 461.l.333910');
        return;
    }

    // Get year range
    const startYear = startYearSelect.value ? parseInt(startYearSelect.value) : null;
    const endYear = endYearSelect.value ? parseInt(endYearSelect.value) : null;

    // Validate year range
    if (startYear && endYear && startYear > endYear) {
        alert('Start year must be before or equal to end year');
        return;
    }

    showProgressSection();

    try {
        const requestBody = { league_key: leagueKey };
        if (startYear) requestBody.start_year = startYear;
        if (endYear) requestBody.end_year = endYear;

        const response = await fetch('/api/report/generate', {
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
function showAuthSection() {
    authSection.classList.remove('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

function showMainSection() {
    authSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

function showProgressSection() {
    authSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    downloadSection.classList.add('hidden');
    errorSection.classList.add('hidden');

    // Reset progress
    updateProgress(0, 'Starting...');
}

function showDownloadSection() {
    authSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    downloadSection.classList.remove('hidden');
    errorSection.classList.add('hidden');
}

function showError(message) {
    authSection.classList.add('hidden');
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
