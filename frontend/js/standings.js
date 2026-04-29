/**
 * Standings Module
 * 
 * Handles display of team standings table.
 */

import { fetchStandings } from './api-client.js';
import { teamNameToSlug, getTeamLogoPath, displayError, displayLoading } from './utils.js';

const REGULAR_SEASON_GAMES = 14;
const NEXT_SEASON_LINK_TEXT = '2026 Season Leaderboard';
const NEXT_SEASON_URL = '';

function isSeasonComplete(standings = []) {
    if (!standings.length) {
        return false;
    }
    return standings.every(team => (team.games_played || 0) >= REGULAR_SEASON_GAMES);
}

function updateStandingsFooter(isSeasonFinal) {
    const footer = document.querySelector('.standings-update-message');
    if (!footer) {
        return;
    }

    if (isSeasonFinal) {
        footer.classList.add('season-final-message');
        const nextSeasonMarkup = NEXT_SEASON_URL
            ? `<a class="season-link-live" href="${NEXT_SEASON_URL}">${NEXT_SEASON_LINK_TEXT}</a>`
            : `<span class="season-link-placeholder">${NEXT_SEASON_LINK_TEXT} (Coming Soon)</span>`;

        footer.innerHTML = `
            Thank you for a great season! Congratulations to the Canadiens for their 1st place finish.
            ${nextSeasonMarkup}
        `;
        return;
    }

    footer.classList.remove('season-final-message');
    footer.textContent = 'Standings updated by 8pm on Mondays';
}

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

    const seasonFinal = isSeasonComplete(standingsData.standings);

    standingsData.standings.forEach((team, index) => {
        const teamSlug = teamNameToSlug(team.team_name);
        const logoPath = getTeamLogoPath(team.team_name);
        const championClass = seasonFinal && index === 0 ? ' champion-row' : '';
        const championLogoClass = seasonFinal && index === 0 ? ' champion-logo' : '';
        const championNameClass = seasonFinal && index === 0 ? ' champion-team-name' : '';
        
        html += `
            <div class="standings-row${championClass}">
                <img class="team-logo${championLogoClass}" src="${logoPath}" alt="${team.team_name}" 
                     onerror="this.style.display='none'">
                <div class="team-name${championNameClass}">
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
    updateStandingsFooter(seasonFinal);
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

