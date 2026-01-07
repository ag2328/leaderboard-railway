/**
 * Game Cards Module
 * 
 * Handles display of game summary cards and team schedules.
 */

import { fetchTeamGames } from './api-client.js';
import { formatDate, formatGameOutcome, getGameOutcomeType, displayError, displayLoading } from './utils.js';
import { getTeamLogoPath } from './utils.js';

/**
 * Render a single game card
 */
export function renderGameCard(game, teamName) {
    const summary = game.summary;
    if (!summary) {
        return '';
    }

    const isHome = game.home_team_name === teamName;
    const opponent = isHome ? game.away_team_name : game.home_team_name;
    const teamScore = isHome ? summary.home_team_score : summary.away_team_score;
    const opponentScore = isHome ? summary.away_team_score : summary.home_team_score;
    const teamShots = isHome ? summary.home_team_shots : summary.away_team_shots;
    const opponentShots = isHome ? summary.away_team_shots : summary.home_team_shots;
    
    const isWinner = summary.winner_team_id === game[isHome ? 'home_team_id' : 'away_team_id'];
    const outcomeType = getGameOutcomeType(summary);
    
    let outcomeClass = '';
    let outcomeText = '';
    if (summary.game_outcome === 'tie') {
        outcomeText = 'T';
        outcomeClass = 't';
    } else if (isWinner) {
        outcomeText = 'W';
        outcomeClass = 'w';
    } else {
        outcomeText = 'L';
        outcomeClass = 'l';
    }
    
    if (outcomeType === 'ot') {
        outcomeText += ' (OT)';
    } else if (outcomeType === 'so') {
        outcomeText += ' (SO)';
    }

    return `
        <div class="game-card">
            <div class="game-card-header">
                <span class="game-date">${formatDate(game.game_date)}</span>
                <span class="game-outcome ${outcomeType}">${outcomeText}</span>
            </div>
            <div class="game-teams">
                <div class="game-team ${isWinner ? 'winner' : ''}">
                    <img src="${getTeamLogoPath(teamName)}" alt="${teamName}" 
                         class="team-logo" onerror="this.style.display='none'">
                    <span>${teamName}</span>
                </div>
                <div class="game-score">${teamScore} - ${opponentScore}</div>
                <div class="game-team ${!isWinner && summary.game_outcome !== 'tie' ? 'winner' : ''}">
                    <img src="${getTeamLogoPath(opponent)}" alt="${opponent}" 
                         class="team-logo" onerror="this.style.display='none'">
                    <span>${opponent}</span>
                </div>
            </div>
            <div class="game-shots">
                <span>Shots: ${teamShots}</span>
                <span>Shots: ${opponentShots}</span>
            </div>
        </div>
    `;
}

/**
 * Render team schedule as a table
 */
export function renderTeamSchedule(games, teamName, container) {
    if (!games || games.length === 0) {
        displayError(container, 'No schedule data available');
        return;
    }

    let html = `
        <div class="schedule-header">
            <div>WK</div>
            <div>DATE</div>
            <div>VS.</div>
            <div>SCORE</div>
            <div>W/L</div>
        </div>
    `;

    games.forEach((game, index) => {
        const summary = game.summary;
        const isHome = game.home_team_name === teamName;
        const opponent = isHome ? game.away_team_name : game.home_team_name;
        
        let scoreDisplay = 'TBD';
        let result = '';
        let isFutureGame = false;

        if (summary) {
            const teamScore = isHome ? summary.home_team_score : summary.away_team_score;
            const opponentScore = isHome ? summary.away_team_score : summary.home_team_score;
            scoreDisplay = `${teamScore}-${opponentScore}`;
            
            if (summary.game_outcome === 'tie') {
                result = 'T';
            } else {
                const isWinner = summary.winner_team_id === game[isHome ? 'home_team_id' : 'away_team_id'];
                result = isWinner ? 'W' : 'L';
            }
        } else {
            isFutureGame = true;
        }

        html += `
            <div class="schedule-row ${isFutureGame ? 'future-game' : ''}">
                <div class="schedule-week">${index + 1}</div>
                <div class="schedule-date">${formatDate(game.game_date)}</div>
                <div class="schedule-opponent">
                    <img src="${getTeamLogoPath(opponent)}" alt="${opponent}" 
                         class="team-logo" onerror="this.style.display='none'">
                    <span>${opponent}</span>
                </div>
                <div class="schedule-score">${scoreDisplay}</div>
                <div class="schedule-result ${result.toLowerCase()}">${result}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * Load and display team games
 */
export async function loadTeamGames(teamId, teamName, container, season = 'Spring 2026') {
    displayLoading(container, 'Loading schedule data...');
    
    try {
        const games = await fetchTeamGames(teamId, season);
        renderTeamSchedule(games, teamName, container);
    } catch (error) {
        console.error('Error loading team games:', error);
        displayError(container, 'Failed to load schedule. Please try again later.');
    }
}

