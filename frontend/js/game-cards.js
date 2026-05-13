/**
 * Game Cards Module
 * 
 * Handles display of game summary cards and team schedules.
 */

import { fetchTeamGames, fetchGameGoalies, fetchGameEventSummary } from './api-client.js';
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
        <div class="game-card-container completed" data-game-id="${game.id}">
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
    const flipper = cardContainer.querySelector('.game-card-flipper, .schedule-game-flipper');
    const gameId = cardContainer.dataset.gameId;
    
    if (!flipper || !gameId) return;

    const { front } = getFlipperSides(flipper);
    if (front && !flipper.dataset.frontHeight) {
        const baseline = front.getBoundingClientRect().height || front.scrollHeight || front.offsetHeight;
        if (baseline > 0) {
            flipper.dataset.frontHeight = `${baseline}`;
        }
    }
    
    // Toggle flip class
    const wasFlipped = flipper.classList.contains('flipped');
    flipper.classList.toggle('flipped');
    ensureFlipperResizeObserver(flipper);
    ensureFlipperTransitionHandler(flipper);

    if (wasFlipped) {
        const baseline = parseFloat(flipper.dataset.frontHeight || '0');
        const frontHeight = front
            ? front.getBoundingClientRect().height || front.scrollHeight || front.offsetHeight
            : 0;
        const target = baseline || frontHeight;
        if (target) {
            flipper.style.height = `${target}px`;
            flipper.dataset.lockedHeight = 'true';
        } else {
            flipper.style.removeProperty('height');
        }
    } else {
        requestAnimationFrame(() => syncFlipperHeight(flipper));
        scheduleFlipHeightReset(flipper);
    }

    if (!flipper.classList.contains('flipped')) {
        const baseline = parseFloat(flipper.dataset.frontHeight || '0');
        const frontHeight = front
            ? front.getBoundingClientRect().height || front.scrollHeight || front.offsetHeight
            : 0;
        const target = baseline || frontHeight;
        if (target) {
            flipper.style.height = `${target}px`;
        } else {
            flipper.style.removeProperty('height');
        }
    }
    
    // If flipping to back, load stats
    if (flipper.classList.contains('flipped')) {
        const backContent = cardContainer.querySelector('.game-card-back-content, .schedule-game-back-content');
        if (backContent && !backContent.dataset.loaded) {
            backContent.innerHTML = '<div class="game-card-back-loading">Loading stats...</div>';
            loadGameStats(gameId, backContent);
            backContent.dataset.loaded = 'true';
        }
    }
}

function getFlipperSides(flipper) {
    const front = flipper.querySelector('.game-card-front, .schedule-game-front');
    const back = flipper.querySelector('.game-card-back, .schedule-game-back');
    const backContent = flipper.querySelector('.game-card-back-content, .schedule-game-back-content');
    return { front, back, backContent };
}

function syncFlipperHeight(flipper) {
    const { front, back, backContent } = getFlipperSides(flipper);
    if (!front || !back) return;

    const frontHeight = front.getBoundingClientRect().height || front.scrollHeight || front.offsetHeight;
    const backHeight = backContent
        ? backContent.getBoundingClientRect().height
        : back.getBoundingClientRect().height;
    const isFlipped = flipper.classList.contains('flipped');
    const storedFrontHeight = parseFloat(flipper.dataset.frontHeight || '0');

    if (!isFlipped && flipper.dataset.lockedHeight === 'true' && storedFrontHeight) {
        flipper.style.height = `${storedFrontHeight}px`;
        return;
    }

    if (!isFlipped && frontHeight > 0) {
        flipper.dataset.frontHeight = `${frontHeight}`;
    }

    const baselineFrontHeight = parseFloat(flipper.dataset.frontHeight || `${frontHeight}`);
    const targetHeight = isFlipped ? backHeight : baselineFrontHeight;
    const fallbackHeight = Math.max(frontHeight, backHeight, baselineFrontHeight, 1);

    flipper.style.height = `${targetHeight || fallbackHeight}px`;
}

function ensureFlipperResizeObserver(flipper) {
    if (flipper._resizeObserver) return;
    const { front, back, backContent } = getFlipperSides(flipper);
    if (!front || !back || typeof ResizeObserver === 'undefined') return;

    const observer = new ResizeObserver(() => syncFlipperHeight(flipper));
    observer.observe(front);
    observer.observe(backContent || back);
    flipper._resizeObserver = observer;
}

function ensureFlipperTransitionHandler(flipper) {
    if (flipper._transitionHandlerAttached) return;
    flipper.addEventListener('transitionend', (event) => {
        if (event.propertyName !== 'transform') return;
        if (!flipper.classList.contains('flipped')) {
            const { front } = getFlipperSides(flipper);
            const baseline = parseFloat(flipper.dataset.frontHeight || '0');
            const frontHeight = front ? front.getBoundingClientRect().height : 0;
            const target = baseline || frontHeight;
            if (target) {
                flipper.style.height = `${target}px`;
            }
            delete flipper.dataset.lockedHeight;
        }
    });
    flipper._transitionHandlerAttached = true;
}

function scheduleFlipHeightReset(flipper) {
    if (flipper.classList.contains('flipped')) return;
    setTimeout(() => {
        if (!flipper.classList.contains('flipped')) {
            syncFlipperHeight(flipper);
        }
    }, 650);
}

/**
 * Load and render game stats on the back of the card
 */
async function loadGameStats(gameId, container) {
    const cardContainer = container.closest('.game-card-container, .schedule-game-card');
    const flipper = cardContainer?.querySelector('.game-card-flipper, .schedule-game-flipper');
    const homeTeam = container.dataset.homeName;
    const awayTeam = container.dataset.awayName;

    try {
        const [summary, goalies] = await Promise.all([
            fetchGameEventSummary(gameId),
            fetchGameGoalies(gameId)
        ]);

        if (!summary) {
            container.innerHTML = '<div class="game-card-back-error">Stats not available</div>';
            if (flipper) {
                requestAnimationFrame(() => syncFlipperHeight(flipper));
            }
            return;
        }

        const homeGoals = summary.goals.home || [];
        const awayGoals = summary.goals.away || [];
        const homeAssists = summary.assists.home || [];
        const awayAssists = summary.assists.away || [];

        const homeGoalies = goalies.filter(g => g.team_id === summary.home_team_id);
        const awayGoalies = goalies.filter(g => g.team_id === summary.away_team_id);

        const renderList = (items, emptyLabel) => {
            if (!items.length) {
                return `<div class="stat-empty">${emptyLabel}</div>`;
            }
            return `<ul>${items.map(item => `<li>${item.player_name} (${item.count})</li>`).join('')}</ul>`;
        };

        const renderGoalies = (items) => {
            if (!items.length) {
                return `<div class="stat-empty">No goalie stats</div>`;
            }
            return items.map(goalie => `
                <div class="goalie-line">
                    <div class="goalie-name">${goalie.name}</div>
                    <div class="goalie-meta">
                        <div>SA ${goalie.shots_against}</div>
                        <div>GA ${goalie.goals_allowed}</div>
                        <div>${formatSavePercentage(goalie.save_percentage)}</div>
                    </div>
                </div>
            `).join('');
        };

        container.innerHTML = `
            <div class="game-back-grid">
                <div class="game-back-column">
                    <div class="game-back-team">${awayTeam}</div>
                    <div class="game-back-section">
                        <div class="game-back-label">Goals</div>
                        ${renderList(awayGoals, 'No goals recorded')}
                    </div>
                    <div class="game-back-section">
                        <div class="game-back-label">Assists</div>
                        ${renderList(awayAssists, 'No assists recorded')}
                    </div>
                    <div class="game-back-section">
                        <div class="game-back-label">Goalie</div>
                        ${renderGoalies(awayGoalies)}
                    </div>
                </div>
                <div class="game-back-column">
                    <div class="game-back-team">${homeTeam}</div>
                    <div class="game-back-section">
                        <div class="game-back-label">Goals</div>
                        ${renderList(homeGoals, 'No goals recorded')}
                    </div>
                    <div class="game-back-section">
                        <div class="game-back-label">Assists</div>
                        ${renderList(homeAssists, 'No assists recorded')}
                    </div>
                    <div class="game-back-section">
                        <div class="game-back-label">Goalie</div>
                        ${renderGoalies(homeGoalies)}
                    </div>
                </div>
            </div>
        `;

        if (flipper) {
            requestAnimationFrame(() => syncFlipperHeight(flipper));
        }
    } catch (error) {
        console.error('Error loading game stats:', error);
        container.innerHTML = '<div class="game-card-back-error">Failed to load stats</div>';
        if (flipper) {
            requestAnimationFrame(() => syncFlipperHeight(flipper));
        }
    }
}

function formatSavePercentage(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) {
        return '0%';
    }
    return `${Math.round(number * 100)}%`;
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
        const cardContainer = e.target.closest('.game-card-container, .schedule-game-card');
        if (cardContainer) {
            handleGameCardClick(cardContainer);
        }
    });

    initGameFlipperHeights();
}

function initGameFlipperHeights() {
    const flippers = document.querySelectorAll('.game-card-flipper');
    if (!flippers.length) return;

    requestAnimationFrame(() => {
        flippers.forEach((flipper) => {
            const { front } = getFlipperSides(flipper);
            if (!front) return;
            const height = front.getBoundingClientRect().height || front.offsetHeight;
            if (height > 0) {
                flipper.dataset.frontHeight = `${height}`;
                flipper.style.height = `${height}px`;
            }
        });
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

    // Games are already sorted by game_date from backend (ORDER BY g.game_date)
    // Just iterate through them in order and group by date as we go
    let html = '';
    let currentDateHeader = null;
    
    games.forEach((game, index) => {
        // Extract date for grouping
        let gameDateKey = null;
        let dateHeader = null;
        
        if (game.game_date) {
            // Extract YYYY-MM-DD from ISO string
            gameDateKey = game.game_date.includes('T') 
                ? game.game_date.split('T')[0] 
                : game.game_date;
            dateHeader = formatScheduleDate(game.game_date);
        } else {
            gameDateKey = 'TBD';
            dateHeader = 'TBD';
        }
        
        // If this is a new date, start a new date section
        if (dateHeader !== currentDateHeader) {
            // Close previous date section if it exists
            if (currentDateHeader !== null) {
                html += `</div>`; // Close schedule-date-section
            }
            
            // Start new date section
            html += `
                <div class="schedule-date-section">
                    <div class="schedule-date-header">${dateHeader}</div>
            `;
            currentDateHeader = dateHeader;
        }
        
        // Render this game as a simple schedule row (both completed and upcoming)
        const summary = game.summary;
        const homeTeam = game.home_team_name;
        const awayTeam = game.away_team_name;
        const isHome = homeTeam === teamName;
        const opponent = isHome ? awayTeam : homeTeam;
        
        let isCompleted = !!summary;
        let result = '';
        let finalStatus = '';
        let teamScore = '';
        let opponentScore = '';

        if (summary) {
            const outcomeType = getGameOutcomeType(summary);
            if (outcomeType === 'ot') {
                finalStatus = 'OT';
            } else if (outcomeType === 'so') {
                finalStatus = 'SO';
            }
            
            teamScore = isHome ? summary.home_team_score : summary.away_team_score;
            opponentScore = isHome ? summary.away_team_score : summary.home_team_score;
            
            if (summary.game_outcome === 'tie') {
                result = 'T';
            } else {
                const isWinner = summary.winner_team_id === game[isHome ? 'home_team_id' : 'away_team_id'];
                result = isWinner ? 'W' : 'L';
            }
        }
        
        const scheduleRow = `
            <div class="schedule-game-row ${isCompleted ? 'completed' : 'upcoming'}">
                <div class="schedule-game-teams">
                    <div class="schedule-game-team">
                        <img src="${getTeamLogoPath(teamName)}" alt="${teamName}" 
                             class="schedule-team-logo" onerror="this.style.display='none'">
                        <span class="schedule-team-name">${teamName}</span>
                        ${isCompleted ? `<span class="schedule-team-score">${teamScore}</span>` : ''}
                    </div>
                    <div class="schedule-game-info">
                        ${
                            isCompleted
                                ? `<span class="schedule-final-status">FINAL${finalStatus ? `/${finalStatus}` : ''}</span>`
                                : '<span class="schedule-game-vs">vs</span>'
                        }
                        ${
                            isCompleted && result
                                ? `<span class="schedule-result-badge ${result.toLowerCase()}">${result}</span>`
                                : ''
                        }
                    </div>
                    <div class="schedule-game-team">
                        <img src="${getTeamLogoPath(opponent)}" alt="${opponent}" 
                             class="schedule-team-logo" onerror="this.style.display='none'">
                        <span class="schedule-team-name">${opponent}</span>
                        ${isCompleted ? `<span class="schedule-team-score">${opponentScore}</span>` : ''}
                    </div>
                </div>
            </div>
        `;

        if (isCompleted) {
            html += `
                <div class="schedule-game-card completed" data-game-id="${game.id}">
                    <div class="schedule-game-flipper">
                        <div class="schedule-game-front">
                            ${scheduleRow}
                        </div>
                        <div class="schedule-game-back">
                            <div class="schedule-game-back-content" data-home-name="${homeTeam}" data-away-name="${awayTeam}">
                                Tap to return
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            html += scheduleRow;
        }
    });
    
    // Close the last date section
    if (currentDateHeader !== null) {
        html += `</div>`;
    }

    container.innerHTML = html;
    initScheduleFlipperHeights(container);
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

function initScheduleFlipperHeights(container) {
    if (!container) return;
    const flippers = container.querySelectorAll('.schedule-game-flipper');
    if (!flippers.length) return;    requestAnimationFrame(() => {
        flippers.forEach((flipper) => {
            const { front } = getFlipperSides(flipper);
            if (!front) return;
            const height = front.getBoundingClientRect().height || front.offsetHeight;
            if (height > 0) {
                flipper.dataset.frontHeight = `${height}`;
                flipper.style.height = `${height}px`;
            }
        });
    });
}