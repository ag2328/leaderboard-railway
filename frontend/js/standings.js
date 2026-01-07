/**
 * Standings Module
 * 
 * Handles display of team standings table.
 */

import { fetchStandings } from './api-client.js';
import { teamNameToSlug, getTeamLogoPath, displayError, displayLoading } from './utils.js';

/**
 * Render the standings table
 */
export function renderStandings(standingsData, container) {
    if (!standingsData || !standingsData.standings || standingsData.standings.length === 0) {
        displayError(container, 'No standings data available');
        return;
    }

    let html = `
        <div class="standings-header">
            <div></div>
            <div>TEAM</div>
            <div>GP</div>
            <div>W</div>
            <div>L</div>
            <div>T</div>
            <div>GS</div>
            <div>PTS</div>
        </div>
    `;

    standingsData.standings.forEach((team) => {
        const teamSlug = teamNameToSlug(team.team_name);
        const logoPath = getTeamLogoPath(team.team_name);
        
        html += `
            <div class="standings-row">
                <img class="team-logo" src="${logoPath}" alt="${team.team_name}" 
                     onerror="this.style.display='none'">
                <div class="team-name">
                    <a href="#team/${teamSlug}" data-team-id="${team.team_id}">${team.team_name}</a>
                </div>
                <div class="team-gp">${team.games_played || 0}</div>
                <div class="team-w">${team.wins || 0}</div>
                <div class="team-l">${team.losses || 0}</div>
                <div class="team-t">${team.ties || 0}</div>
                <div class="team-gs">${team.goals_scored || 0}</div>
                <div class="team-pts">${team.points || 0}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * Load and display standings
 */
export async function loadStandings(container, season = 'Spring 2026') {
    displayLoading(container, 'Loading standings data...');
    
    try {
        const standingsData = await fetchStandings(season);
        renderStandings(standingsData, container);
    } catch (error) {
        console.error('Error loading standings:', error);
        displayError(container, 'Failed to load standings. Please try again later.');
    }
}

