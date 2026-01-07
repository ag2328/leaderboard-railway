/**
 * Game Cards Module
 * 
 * Handles display of game summary cards and team schedules.
 */

import { fetchTeamGames, fetchGameGoalies, fetchGamePeriodStats } from './api-client.js';
import { formatDate, formatGameOutcome, getGameOutcomeType, displayError, displayLoading } from './utils.js';
import { getTeamLogoPath } from './utils.js';

/**
 * Render a single game card (Apple Sports style) with flip functionality
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

    const homeTeam = game.home_team_name;
    const awayTeam = game.away_team_name;
    const homeTeamId = game.home_team_id;
    const awayTeamId = game.away_team_id;

    return `
        <div class="game-card-container" data-game-id="${game.id}">
            <div class="game-card-flipper">
                <div class="game-card-front">
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
                <div class="game-card-back">
                    <div class="game-card-back-content" data-home-team="${homeTeamId}" data-away-team="${awayTeamId}" 
                         data-home-name="${homeTeam}" data-away-name="${awayTeam}">
                        <div class="game-card-back-loading">Loading stats...</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Handle game card click to flip
 */
function handleGameCardClick(cardContainer) {
    const flipper = cardContainer.querySelector('.game-card-flipper');
    const gameId = cardContainer.dataset.gameId;
    
    if (!flipper || !gameId) return;
    
    // Toggle flip class
    flipper.classList.toggle('flipped');
    
    // If flipping to back, load stats
    if (flipper.classList.contains('flipped')) {
        const backContent = cardContainer.querySelector('.game-card-back-content');
        if (backContent && !backContent.dataset.loaded) {
            loadGameStats(gameId, backContent);
            backContent.dataset.loaded = 'true';
        }
    }
}

/**
 * Load and render game stats on the back of the card
 */
async function loadGameStats(gameId, container) {
    const homeTeam = container.dataset.homeName;
    const awayTeam = container.dataset.awayName;
    
    try {
        const stats = await fetchGamePeriodStats(gameId);
        
        if (!stats) {
            container.innerHTML = '<div class="game-card-back-error">Stats not available</div>';
            return;
        }
        
        // Render period scores table
        let scoresHtml = `
            <div class="game-card-stats-section">
                <table class="game-card-stats-table">
                    <thead>
                        <tr>
                            <th></th>
                            ${stats.periods.map(p => `<th>${getPeriodLabel(p)}</th>`).join('')}
                            <th>T</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="team-cell">
                                <img src="${getTeamLogoPath(homeTeam)}" alt="${homeTeam}" 
                                     class="team-logo-small" onerror="this.style.display='none'">
                                <span class="team-abbrev">${getTeamAbbreviation(homeTeam)}</span>
                            </td>
                            ${stats.goals.home.map(goals => `<td>${goals}</td>`).join('')}
                            <td class="total-cell">${stats.totals.goals.home}</td>
                        </tr>
                        <tr>
                            <td class="team-cell">
                                <img src="${getTeamLogoPath(awayTeam)}" alt="${awayTeam}" 
                                     class="team-logo-small" onerror="this.style.display='none'">
                                <span class="team-abbrev">${getTeamAbbreviation(awayTeam)}</span>
                            </td>
                            ${stats.goals.away.map(goals => `<td>${goals}</td>`).join('')}
                            <td class="total-cell">${stats.totals.goals.away}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
        
        // Render shots on goal table
        scoresHtml += `
            <div class="game-card-stats-section">
                <h3 class="game-card-stats-title">Shots On Goal</h3>
                <table class="game-card-stats-table">
                    <thead>
                        <tr>
                            <th>Period</th>
                            <th>${getTeamAbbreviation(homeTeam)}</th>
                            <th>${getTeamAbbreviation(awayTeam)}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${stats.periods.map((period, idx) => `
                            <tr>
                                <td>${getPeriodLabel(period)}</td>
                                <td>${stats.shots.home[idx] || 0}</td>
                                <td>${stats.shots.away[idx] || 0}</td>
                            </tr>
                        `).join('')}
                        <tr class="total-row">
                            <td>Total</td>
                            <td class="total-cell">${stats.totals.shots.home}</td>
                            <td class="total-cell">${stats.totals.shots.away}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = scoresHtml;
    } catch (error) {
        console.error('Error loading game stats:', error);
        container.innerHTML = '<div class="game-card-back-error">Failed to load stats</div>';
    }
}

/**
 * Get period label (1st, 2nd, 3rd, etc.)
 */
function getPeriodLabel(period) {
    const labels = ['1st', '2nd', '3rd', '4th', '5th'];
    return labels[period - 1] || `${period}th`;
}

/**
 * Get team abbreviation from full name
 */
function getTeamAbbreviation(teamName) {
    const abbreviations = {
        'Bruins': 'BRU',
        'Canadiens': 'MON',
        'Maple Leafs': 'TOR',
        'Red Wings': 'DET'
    };
    return abbreviations[teamName] || teamName.substring(0, 3).toUpperCase();
}

/**
 * Initialize game card interactions after rendering
 */
export function initGameCards() {
    document.addEventListener('click', (e) => {
        const cardContainer = e.target.closest('.game-card-container');
        if (cardContainer) {
            handleGameCardClick(cardContainer);
        }
    });
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
            const homeTeam = game.home_team_name;
            const awayTeam = game.away_team_name;
            const isHome = homeTeam === teamName;
            
            let isCompleted = !!summary;
            let result = '';
            let finalStatus = '';

            if (summary) {
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

            // Determine winners
            const homeIsWinner = summary && summary.winner_team_id === game.home_team_id && summary.game_outcome !== 'tie';
            const awayIsWinner = summary && summary.winner_team_id === game.away_team_id && summary.game_outcome !== 'tie';

            html += `
                <div class="schedule-game-row ${isCompleted ? 'completed' : 'upcoming'}">
                    <div class="schedule-game-teams">
                        <div class="schedule-game-team ${homeIsWinner ? 'winner' : ''}">
                            <img src="${getTeamLogoPath(homeTeam)}" alt="${homeTeam}" 
                                 class="schedule-team-logo" onerror="this.style.display='none'">
                            <span class="schedule-team-name">${homeTeam}</span>
                            ${isCompleted ? `<span class="schedule-team-score">${summary.home_team_score}</span>` : ''}
                        </div>
                        <div class="schedule-game-info">
                            ${isCompleted ? `<span class="schedule-final-status">${finalStatus || 'Final'}</span>` : '<span class="schedule-game-vs">vs</span>'}
                        </div>
                        <div class="schedule-game-team ${awayIsWinner ? 'winner' : ''}">
                            <img src="${getTeamLogoPath(awayTeam)}" alt="${awayTeam}" 
                                 class="schedule-team-logo" onerror="this.style.display='none'">
                            <span class="schedule-team-name">${awayTeam}</span>
                            ${isCompleted ? `<span class="schedule-team-score">${summary.away_team_score}</span>` : ''}
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

