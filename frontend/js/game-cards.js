/**
 * Game Cards Module
 * 
 * Handles display of game summary cards and team schedules.
 */

import { fetchTeamGames, fetchGameGoalies } from './api-client.js';
import { formatDate, formatGameOutcome, getGameOutcomeType, displayError, displayLoading } from './utils.js';
import { getTeamLogoPath } from './utils.js';

/**
 * Render a single game card (Apple Sports style)
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
    
    const isWinner = summary.winner_team_id === game[isHome ? 'home_team_id' : 'away_team_id'];
    const outcomeType = getGameOutcomeType(summary);
    
    // Determine final status text
    let finalStatus = 'Final';
    if (outcomeType === 'ot') {
        finalStatus = 'Final OT';
    } else if (outcomeType === 'so') {
        finalStatus = 'Final SO';
    }

    return `
        <div class="game-card">
            <div class="game-card-date">${formatDate(game.game_date)}</div>
            <div class="game-card-scoreboard">
                <div class="game-card-team-section ${isWinner ? 'winner' : ''}">
                    <img src="${getTeamLogoPath(teamName)}" alt="${teamName}" 
                         class="game-card-logo" onerror="this.style.display='none'">
                    <div class="game-card-team-name">${teamName}</div>
                    <div class="game-card-score">${teamScore}</div>
                </div>
                <div class="game-card-status">${finalStatus}</div>
                <div class="game-card-team-section ${!isWinner && summary.game_outcome !== 'tie' ? 'winner' : ''}">
                    <img src="${getTeamLogoPath(opponent)}" alt="${opponent}" 
                         class="game-card-logo" onerror="this.style.display='none'">
                    <div class="game-card-team-name">${opponent}</div>
                    <div class="game-card-score">${opponentScore}</div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Format date for schedule headers (e.g., "Fri, Jan 9")
 */
function formatScheduleDate(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const dayName = days[date.getDay()];
        const month = months[date.getMonth()];
        const day = date.getDate();
        return `${dayName}, ${month} ${day}`;
    } catch (e) {
        return formatDate(dateString);
    }
}

/**
 * Format time for games (e.g., "7:00 PM")
 */
function formatGameTime(dateString) {
    if (!dateString) return 'TBD';
    
    try {
        const date = new Date(dateString);
        // If no time is set, default to 7:00 PM
        if (date.getHours() === 0 && date.getMinutes() === 0) {
            return '7:00 PM';
        }
        const hours = date.getHours();
        const minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const displayHours = hours % 12 || 12;
        const displayMinutes = minutes.toString().padStart(2, '0');
        return `${displayHours}:${displayMinutes} ${ampm}`;
    } catch (e) {
        return 'TBD';
    }
}

/**
 * Render team schedule (Apple Sports style)
 */
export async function renderTeamSchedule(games, teamName, container) {
    if (!games || games.length === 0) {
        displayError(container, 'No schedule data available');
        return;
    }

    // Fetch goalie stats for all completed games in parallel
    const goalieStatsPromises = games
        .filter(game => game.summary)
        .map(game => 
            fetchGameGoalies(game.id)
                .then(goalies => ({ gameId: game.id, goalies }))
                .catch(error => {
                    console.warn(`Failed to fetch goalie stats for game ${game.id}:`, error);
                    return { gameId: game.id, goalies: [] };
                })
        );
    
    const goalieStatsResults = await Promise.all(goalieStatsPromises);
    const goalieStatsMap = new Map(goalieStatsResults.map(r => [r.gameId, r.goalies]));

    // Group games by date
    const gamesByDate = {};
    games.forEach(game => {
        const dateKey = game.game_date ? new Date(game.game_date).toDateString() : 'TBD';
        if (!gamesByDate[dateKey]) {
            gamesByDate[dateKey] = [];
        }
        gamesByDate[dateKey].push(game);
    });

    let html = '';

    // Render games grouped by date
    Object.keys(gamesByDate).sort().forEach(dateKey => {
        const dateGames = gamesByDate[dateKey];
        const firstGame = dateGames[0];
        const dateHeader = formatScheduleDate(firstGame.game_date);
        
        html += `
            <div class="schedule-date-section">
                <div class="schedule-date-header">${dateHeader}</div>
        `;

        dateGames.forEach((game, index) => {
            const summary = game.summary;
            const isHome = game.home_team_name === teamName;
            const opponent = isHome ? game.away_team_name : game.home_team_name;
            
            let isCompleted = !!summary;
            let scoreDisplay = '';
            let result = '';
            let finalStatus = '';

            if (summary) {
                const teamScore = isHome ? summary.home_team_score : summary.away_team_score;
                const opponentScore = isHome ? summary.away_team_score : summary.home_team_score;
                scoreDisplay = `${teamScore}-${opponentScore}`;
                
                const outcomeType = getGameOutcomeType(summary);
                if (outcomeType === 'ot') {
                    finalStatus = 'OT';
                } else if (outcomeType === 'so') {
                    finalStatus = 'SO';
                }
                
                if (summary.game_outcome === 'tie') {
                    result = 'T';
                } else {
                    const isWinner = summary.winner_team_id === game[isHome ? 'home_team_id' : 'away_team_id'];
                    result = isWinner ? 'W' : 'L';
                }
            }

            const gameTime = isCompleted ? '' : formatGameTime(game.game_date);
            const teamIsWinner = summary && summary.winner_team_id === game[isHome ? 'home_team_id' : 'away_team_id'];
            const opponentIsWinner = summary && summary.winner_team_id === game[isHome ? 'away_team_id' : 'home_team_id'] && summary.game_outcome !== 'tie';

            html += `
                <div class="schedule-game-row ${isCompleted ? 'completed' : 'upcoming'}">
                    <div class="schedule-game-teams">
                        <div class="schedule-game-team ${teamIsWinner ? 'winner' : ''}">
                            <img src="${getTeamLogoPath(teamName)}" alt="${teamName}" 
                                 class="schedule-team-logo" onerror="this.style.display='none'">
                            <span class="schedule-team-name">${teamName}</span>
                            ${isCompleted ? `<span class="schedule-team-score">${isHome ? summary.home_team_score : summary.away_team_score}</span>` : ''}
                        </div>
                        <div class="schedule-game-info">
                            ${isCompleted ? `<span class="schedule-final-status">${finalStatus || 'Final'}</span>` : `<span class="schedule-game-time">${gameTime}</span>`}
                        </div>
                        <div class="schedule-game-team ${opponentIsWinner ? 'winner' : ''}">
                            <img src="${getTeamLogoPath(opponent)}" alt="${opponent}" 
                                 class="schedule-team-logo" onerror="this.style.display='none'">
                            <span class="schedule-team-name">${opponent}</span>
                            ${isCompleted ? `<span class="schedule-team-score">${isHome ? summary.away_team_score : summary.home_team_score}</span>` : ''}
                        </div>
                    </div>
                    ${isCompleted && result ? `<div class="schedule-result-badge ${result.toLowerCase()}">${result}</div>` : ''}
                </div>
            `;
        });

        html += `</div>`;
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
        await renderTeamSchedule(games, teamName, container);
    } catch (error) {
        console.error('Error loading team games:', error);
        displayError(container, 'Failed to load schedule. Please try again later.');
    }
}

