/**
 * Utility Functions
 * 
 * Helper functions used across the application.
 */

/**
 * Convert team name to slug (for URLs and file paths)
 */
export function teamNameToSlug(teamName) {
    return teamName.toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_]/g, '');
}

/**
 * Format team name from slug
 */
export function slugToTeamName(slug) {
    return slug.replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Get team logo path
 */
export function getTeamLogoPath(teamName) {
    const slug = teamNameToSlug(teamName);
    return `static/logos/${slug}.png`;
}

/**
 * Format date string
 */
export function formatDate(dateString) {
    if (!dateString) return 'TBD';
    
    try {
        const date = new Date(dateString);
        const month = date.getMonth() + 1;
        const day = date.getDate();
        return `${month}/${day}`;
    } catch (e) {
        return dateString;
    }
}

/**
 * Format game outcome badge
 */
export function formatGameOutcome(outcome) {
    const outcomes = {
        'regulation_win': 'W',
        'regulation_loss': 'L',
        'tie': 'T',
        'ot_win': 'OT W',
        'ot_loss': 'OT L',
        'so_win': 'SO W',
        'so_loss': 'SO L'
    };
    return outcomes[outcome] || outcome;
}

/**
 * Get game outcome class for styling
 */
export function getGameOutcomeClass(outcome) {
    if (outcome.includes('ot_') || outcome.includes('so_')) {
        return outcome.includes('win') ? 'ot' : 'so';
    }
    return '';
}

/**
 * Determine if game went to overtime or shootout
 */
export function getGameOutcomeType(summary) {
    if (summary.went_to_shootout) {
        return 'so';
    } else if (summary.went_to_overtime) {
        return 'ot';
    }
    return 'regulation';
}

/**
 * Display error message
 */
export function displayError(container, message) {
    if (container) {
        container.innerHTML = `<div class="error">${message}</div>`;
    }
}

/**
 * Display loading message
 */
export function displayLoading(container, message = 'Loading...') {
    if (container) {
        container.innerHTML = `<div class="loading">${message}</div>`;
    }
}

