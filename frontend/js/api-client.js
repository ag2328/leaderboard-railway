/**
 * API Client Module
 * 
 * Handles all API communication with the backend.
 * Provides functions for fetching standings, games, players, etc.
 */

const API_BASE_URL = window.location.origin.includes('localhost') 
    ? 'http://localhost:5000/api'
    : '/api';

/**
 * Fetch team standings for a season
 */
export async function fetchStandings(season = 'Spring 2026') {
    try {
        const response = await fetch(`${API_BASE_URL}/standings?season=${encodeURIComponent(season)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching standings:', error);
        throw error;
    }
}

/**
 * Fetch all teams
 */
export async function fetchTeams() {
    try {
        const response = await fetch(`${API_BASE_URL}/teams`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.teams;
    } catch (error) {
        console.error('Error fetching teams:', error);
        throw error;
    }
}

/**
 * Fetch games for a team in a season
 */
export async function fetchTeamGames(teamId, season = 'Spring 2026') {
    try {
        const response = await fetch(`${API_BASE_URL}/teams/${teamId}/games?season=${encodeURIComponent(season)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.games;
    } catch (error) {
        console.error('Error fetching team games:', error);
        throw error;
    }
}

/**
 * Fetch player statistics for a team in a season
 */
export async function fetchTeamPlayers(teamId, season = 'Spring 2026') {
    try {
        const response = await fetch(`${API_BASE_URL}/teams/${teamId}/players?season=${encodeURIComponent(season)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.players;
    } catch (error) {
        console.error('Error fetching team players:', error);
        throw error;
    }
}

/**
 * Fetch goalie statistics for a team in a season
 */
export async function fetchTeamGoalie(teamId, season = 'Spring 2026') {
    try {
        const response = await fetch(`${API_BASE_URL}/teams/${teamId}/goalie?season=${encodeURIComponent(season)}`);
        if (!response.ok) {
            if (response.status === 404) {
                return null; // No goalie found
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.goalie;
    } catch (error) {
        console.error('Error fetching team goalie:', error);
        return null;
    }
}

/**
 * Fetch a specific game
 */
export async function fetchGame(gameId) {
    try {
        const response = await fetch(`${API_BASE_URL}/games/${gameId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.game;
    } catch (error) {
        console.error('Error fetching game:', error);
        throw error;
    }
}

/**
 * Fetch goalie stats for a specific game
 */
export async function fetchGameGoalies(gameId) {
    try {
        const response = await fetch(`${API_BASE_URL}/games/${gameId}/goalies`);
        if (!response.ok) {
            if (response.status === 404) {
                return []; // No goalies found
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.goalies || [];
    } catch (error) {
        console.error('Error fetching game goalies:', error);
        return [];
    }
}

/**
 * Health check
 */
export async function healthCheck() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Health check failed:', error);
        throw error;
    }
}

