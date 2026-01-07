/**
 * Player Stats Module
 * 
 * Handles display of player and goalie statistics.
 */

import { fetchTeamPlayers, fetchTeamGoalie } from './api-client.js';
import { displayError, displayLoading } from './utils.js';

/**
 * Render player statistics table
 */
export function renderPlayerStats(players, container) {
    if (!players || players.length === 0) {
        displayError(container, 'No player statistics available');
        return;
    }

    // Separate skaters and goalies
    const skaters = players.filter(p => !p.is_goalie);
    const goalies = players.filter(p => p.is_goalie);

    // Sort skaters by jersey number
    const sortedSkaters = [...skaters].sort((a, b) => {
        const numA = a.jersey_number || 999;
        const numB = b.jersey_number || 999;
        return numA - numB;
    });

    let html = `
        <div class="player-stats-title">Player Statistics</div>
        <table class="player-stats-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Player</th>
                    <th>G</th>
                    <th>A</th>
                    <th>P</th>
                </tr>
            </thead>
            <tbody>
    `;

    // Render skaters
    sortedSkaters.forEach(player => {
        const goals = player.goals || 0;
        const assists = player.assists || 0;
        const penalties = player.penalties || 0;
        const points = goals + assists;

        html += `
            <tr>
                <td>${player.jersey_number || '-'}</td>
                <td>${player.name}</td>
                <td>${goals}</td>
                <td>${assists}</td>
                <td>${penalties}</td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    // Render goalies if available
    if (goalies.length > 0) {
        html += `
            <div class="player-stats-title" style="margin-top: var(--spacing-xl);">Goaltender Statistics</div>
            <table class="player-stats-table">
                <thead>
                    <tr class="goalie-header-row">
                        <th>#</th>
                        <th>Goalie</th>
                        <th>SA</th>
                        <th>GA</th>
                        <th>SV</th>
                        <th>SV%</th>
                    </tr>
                </thead>
                <tbody>
        `;

        goalies.forEach(goalie => {
            const shotsAgainst = goalie.shots_against || 0;
            const goalsAllowed = goalie.goals_allowed || 0;
            const saves = goalie.saves || 0;
            const savePct = goalie.save_percentage ? goalie.save_percentage.toFixed(3) : '-';

            html += `
                <tr class="goalie-row">
                    <td>${goalie.jersey_number || '-'}</td>
                    <td>${goalie.name}</td>
                    <td>${shotsAgainst}</td>
                    <td>${goalsAllowed}</td>
                    <td>${saves}</td>
                    <td>${savePct}</td>
                </tr>
            `;
        });

        html += `
                </tbody>
            </table>
        `;
    }

    container.innerHTML = html;
}

/**
 * Load and display player statistics
 */
export async function loadPlayerStats(teamId, container, season = 'Spring 2026') {
    displayLoading(container, 'Loading player statistics...');
    
    try {
        const players = await fetchTeamPlayers(teamId, season);
        
        // Also try to get goalie stats separately (if needed)
        const goalie = await fetchTeamGoalie(teamId, season);
        
        // Merge goalie data if available
        if (goalie) {
            const goalieInPlayers = players.find(p => p.id === goalie.id);
            if (!goalieInPlayers) {
                players.push({
                    ...goalie,
                    is_goalie: true,
                    shots_against: goalie.shots_against,
                    goals_allowed: goalie.goals_allowed,
                    saves: goalie.saves,
                    save_percentage: goalie.save_percentage
                });
            } else {
                Object.assign(goalieInPlayers, {
                    is_goalie: true,
                    shots_against: goalie.shots_against,
                    goals_allowed: goalie.goals_allowed,
                    saves: goalie.saves,
                    save_percentage: goalie.save_percentage
                });
            }
        }
        
        renderPlayerStats(players, container);
    } catch (error) {
        console.error('Error loading player stats:', error);
        displayError(container, 'Failed to load player statistics. Please try again later.');
    }
}

