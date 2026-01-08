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
        <div class="player-stats-title">Player Stats</div>
        <table class="player-stats-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>NAME</th>
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
        const points = goals + assists;

        html += `
            <tr>
                <td>${player.jersey_number || '-'}</td>
                <td>${player.name}</td>
                <td>${goals}</td>
                <td>${assists}</td>
                <td>${points}</td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    // Render goalies if available (centered, no heading)
    if (goalies.length > 0) {
        html += `
            <div class="goalie-stats-container">
                <table class="player-stats-table goalie-stats-table">
                    <thead>
                        <tr class="goalie-header-row">
                            <th>#</th>
                            <th>Name</th>
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
            // Show 0.000 for zero stats, otherwise format the percentage
            const savePct = (goalie.save_percentage !== null && goalie.save_percentage !== undefined) 
                ? parseFloat(goalie.save_percentage).toFixed(3) 
                : '0.000';

            html += `
                <tr class="goalie-row">
                    <td>${goalie.jersey_number || '-'}</td>
                    <td>${goalie.name || 'Unknown'}</td>
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
            </div>
        `;
    }

    // Add legend and update message
    html += `
        <div class="stats-legend">
            <div class="legend-title">Legend</div>
            <div class="legend-items">
                <div class="legend-item"><span class="legend-key">G:</span> Goals</div>
                <div class="legend-item"><span class="legend-key">A:</span> Assists</div>
                <div class="legend-item"><span class="legend-key">P:</span> Penalties</div>
                <div class="legend-item"><span class="legend-key">SA:</span> Shots Against</div>
                <div class="legend-item"><span class="legend-key">GA:</span> Goals Allowed</div>
                <div class="legend-item"><span class="legend-key">SV:</span> Saves</div>
                <div class="legend-item"><span class="legend-key">SV%:</span> Save Percentage</div>
            </div>
        </div>
        <div class="stats-update-message">Standings updated by 8pm on Mondays</div>
    `;

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
            // Ensure goalie has all required fields with defaults
            const goalieData = {
                ...goalie,
                id: goalie.id || goalie.goalie_id,
                is_goalie: true,
                name: goalie.name || 'Unknown',
                jersey_number: goalie.jersey_number || null,
                shots_against: goalie.shots_against || 0,
                goals_allowed: goalie.goals_allowed || 0,
                saves: goalie.saves || 0,
                save_percentage: goalie.save_percentage || 0.0
            };
            
            // Check if goalie is already in players list (shouldn't be, but just in case)
            const goalieInPlayers = players.find(p => p.id === goalieData.id);
            if (!goalieInPlayers) {
                players.push(goalieData);
            } else {
                Object.assign(goalieInPlayers, goalieData);
            }
        } else {
            console.warn(`No goalie found for team ${teamId} in season ${season}`);
        }
        
        renderPlayerStats(players, container);
    } catch (error) {
        console.error('Error loading player stats:', error);
        displayError(container, 'Failed to load player statistics. Please try again later.');
    }
}

