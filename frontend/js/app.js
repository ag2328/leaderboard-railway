/**
 * Main Application Module
 * 
 * Handles routing, page navigation, and initialization.
 */

import { loadStandings } from './standings.js';
import { loadTeamGames } from './game-cards.js';
import { loadPlayerStats } from './player-stats.js';
import { fetchTeams } from './api-client.js';
import { slugToTeamName, getTeamLogoPath } from './utils.js';

// DOM Elements
const standingsPage = document.getElementById('standings-page');
const teamPage = document.getElementById('team-page');
const standingsContainer = document.getElementById('standings-container');
const scheduleContainer = document.getElementById('schedule-container');
const playerStatsContainer = document.getElementById('player-stats-container');
const teamTitle = document.getElementById('team-title');
const teamLogo = document.getElementById('team-logo');
const backToStandingsLink = document.getElementById('back-to-standings');

// State
let teamsCache = null;
let currentTeamId = null;
let currentTeamName = null;

/**
 * Initialize the application
 */
async function init() {
    try {
        // Load teams cache
        teamsCache = await fetchTeams();
        
        // Set up hash change listener
        window.addEventListener('hashchange', handleHashChange);
        
        // Handle initial hash
        await handleHashChange();
        
        // Set up back button
        if (backToStandingsLink) {
            backToStandingsLink.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.hash = '';
            });
        }
    } catch (error) {
        console.error('Error initializing app:', error);
        displayError(standingsContainer, 'Failed to initialize application. Please refresh the page.');
    }
}

/**
 * Handle hash changes for routing
 */
async function handleHashChange() {
    const hash = window.location.hash;
    
    if (hash.startsWith('#team/')) {
        // Show team page
        const teamSlug = hash.replace('#team/', '');
        const teamName = slugToTeamName(teamSlug);
        
        // Find team ID from cache
        const team = teamsCache?.find(t => 
            t.name.toLowerCase().replace(/\s+/g, '_') === teamSlug
        );
        
        if (team) {
            currentTeamId = team.id;
            currentTeamName = team.name;
            await showTeamPage(team.id, team.name);
        } else {
            displayError(scheduleContainer, 'Team not found');
        }
    } else {
        // Show standings page
        showStandingsPage();
    }
}

/**
 * Show standings page
 */
function showStandingsPage() {
    standingsPage.classList.remove('hidden');
    teamPage.classList.add('hidden');
    loadStandings(standingsContainer);
}

/**
 * Show team page
 */
async function showTeamPage(teamId, teamName) {
    standingsPage.classList.add('hidden');
    teamPage.classList.remove('hidden');
    
    // Update team header
    if (teamTitle) {
        teamTitle.textContent = `${teamName} Schedule`;
    }
    
    if (teamLogo) {
        const logoPath = getTeamLogoPath(teamName);
        teamLogo.innerHTML = `<img src="${logoPath}" alt="${teamName}" onerror="this.style.display='none'">`;
    }
    
    // Load team games
    await loadTeamGames(teamId, teamName, scheduleContainer);
    
    // Load player stats
    await loadPlayerStats(teamId, playerStatsContainer);
}

/**
 * Display error message
 */
function displayError(container, message) {
    if (container) {
        container.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

