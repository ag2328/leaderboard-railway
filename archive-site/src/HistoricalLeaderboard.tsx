"use client";

import { useEffect, useMemo, useState } from "react";
import data from "./historical-data.json";

const n = (value?: string) => Number(value || 0);
const teams = Object.fromEntries(data.teams.map((team) => [team.id, team]));
const summaries = Object.fromEntries(data.summaries.map((summary) => [summary.game_id, summary]));
const players = Object.fromEntries(data.players.map((player) => [player.id, player]));
const goalies = Object.fromEntries(data.goalies.map((goalie) => [goalie.id, goalie]));
const logo = (teamName: string) => `./logos/${teamName.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "")}.png`;

function teamSlug(name: string) { return name.toLowerCase().replace(/\s+/g, "_"); }
function prettyDate(value: string) { return new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(`${value.slice(0, 10)}T12:00:00Z`)); }

export function HistoricalLeaderboard() {
  const [teamId, setTeamId] = useState<string | null>(null);
  const [expandedGame, setExpandedGame] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => {
      const slug = window.location.hash.replace(/^#team\//, "");
      const team = data.teams.find((item) => teamSlug(item.name) === slug);
      setTeamId(team?.id || null);
      window.scrollTo(0, 0);
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const standings = useMemo(() => [...data.standings].sort((a, b) => n(b.points) - n(a.points) || n(b.wins) - n(a.wins)), []);
  const selectedTeam = teamId ? teams[teamId] : null;

  if (!selectedTeam) {
    return (
      <main id="standings-page" className="screen">
        <div className="app-header">
          <div className="app-logo" />
          <h1 className="app-title">Legends Hockey</h1>
          <p className="app-subtitle">In-House 14/16U League</p>
          <p className="app-season">Spring 2026</p>
        </div>
        <div className="standings-container">
          <div className="standings-header"><div></div><div className="header-team">TEAM</div><div>GP</div><div>W</div><div>L</div><div>T</div><div>GS</div><div className="header-pts">PTS</div></div>
          {standings.map((row) => {
            const team = teams[row.team_id];
            return <div className="standings-row" key={row.id}><div><img className="team-logo" src={logo(team.name)} alt={`${team.name} logo`} /></div><div className="team-name"><a href={`#team/${teamSlug(team.name)}`}>{team.name}</a></div><div className="team-gp">{row.games_played}</div><div className="team-w">{row.wins}</div><div className="team-l">{row.losses}</div><div className="team-t">{row.ties}</div><div className="team-gs">{row.goals_scored}</div><div className="team-pts">{row.points}</div></div>;
          })}
        </div>
        <div className="standings-update-message">Final Spring 2026 standings · Read-only historical archive</div>
      </main>
    );
  }

  const teamGames = [...data.games].filter((game) => game.home_team_id === teamId || game.away_team_id === teamId).sort((a, b) => a.game_date.localeCompare(b.game_date));
  const skaters = data.playerStats.filter((stat) => stat.team_id === teamId).map((stat) => ({ ...players[stat.player_id], ...stat })).sort((a, b) => n(a.jersey_number) - n(b.jersey_number));
  const teamGoalies = data.goalieStats.filter((stat) => stat.team_id === teamId).map((stat) => ({ ...goalies[stat.goalie_id], ...stat }));

  return (
    <main id="team-page" className="screen">
      <div className="app-header">
        <div className="app-logo"><img src={logo(selectedTeam.name)} alt={`${selectedTeam.name} logo`} /></div>
        <h1 className="app-title">{selectedTeam.name}</h1>
        <a href="#" className="back-link">← Back to Standings</a>
      </div>
      <div className="schedule-container">
        {teamGames.map((game) => {
          const home = teams[game.home_team_id]; const away = teams[game.away_team_id]; const summary = summaries[game.id]; const selectedIsHome = game.home_team_id === teamId; const opponent = selectedIsHome ? away : home;
          const teamScore = summary ? (selectedIsHome ? summary.home_team_score : summary.away_team_score) : ""; const opponentScore = summary ? (selectedIsHome ? summary.away_team_score : summary.home_team_score) : "";
          const tied = summary?.game_outcome === "tie"; const won = summary && !tied && summary.winner_team_id === teamId; const result = tied ? "T" : won ? "W" : "L";
          const overtime = summary?.went_to_shootout === "t" ? "/SO" : summary?.went_to_overtime === "t" ? "/OT" : "";
          return <div className="schedule-date-section" key={game.id}><div className="schedule-date-header">Week {game.week} · {prettyDate(game.game_date)}</div><button className="schedule-game-row completed" onClick={() => setExpandedGame(expandedGame === game.id ? null : game.id)} aria-expanded={expandedGame === game.id}><div className="schedule-game-teams"><div className={`schedule-game-team ${won ? "winner" : ""}`}><img src={logo(selectedTeam.name)} alt="" className="schedule-team-logo" /><span className="schedule-team-name">{selectedTeam.name}</span><span className="schedule-team-score">{teamScore}</span></div><div className="schedule-game-info"><span className="schedule-final-status">FINAL{overtime}</span><span className={`schedule-result-badge ${result.toLowerCase()}`}>{result}</span></div><div className={`schedule-game-team ${summary && !tied && !won ? "winner" : ""}`}><img src={logo(opponent.name)} alt="" className="schedule-team-logo" /><span className="schedule-team-name">{opponent.name}</span><span className="schedule-team-score">{opponentScore}</span></div></div></button>{expandedGame === game.id && <GameDetails gameId={game.id} />}</div>;
        })}
      </div>
      <div className="player-stats-container">
        <div className="player-stats-title">Player Stats</div>
        <table className="player-stats-table"><thead><tr><th>#</th><th>NAME</th><th>G</th><th>A</th><th>P</th></tr></thead><tbody>{skaters.map((player) => <tr key={player.id}><td>{player.jersey_number || "-"}</td><td className="player-name-cell">{player.name}</td><td>{player.goals}</td><td>{player.assists}</td><td>{player.points}</td></tr>)}</tbody></table>
        {teamGoalies.length > 0 && <div className="goalie-stats-container"><table className="player-stats-table goalie-stats-table"><thead><tr className="goalie-header-row"><th>#</th><th>Name</th><th>SA</th><th>GA</th><th>SV</th><th>SV%</th></tr></thead><tbody>{teamGoalies.map((goalie) => <tr className="goalie-row" key={goalie.id}><td>{goalie.jersey_number || "-"}</td><td>{goalie.name}</td><td>{goalie.shots_against}</td><td>{goalie.goals_allowed}</td><td>{goalie.saves}</td><td>{Number(goalie.save_percentage).toFixed(3)}</td></tr>)}</tbody></table></div>}
        <div className="stats-legend"><div className="legend-title">Legend</div><div className="legend-items"><div className="legend-line"><div className="legend-item"><span className="legend-key">G:</span> Goals</div><div className="legend-item"><span className="legend-key">A:</span> Assists</div><div className="legend-item"><span className="legend-key">P:</span> Points</div></div><div className="legend-line"><div className="legend-item"><span className="legend-key">SA:</span> Shots Against</div><div className="legend-item"><span className="legend-key">GA:</span> Goals Allowed</div><div className="legend-item"><span className="legend-key">SV:</span> Saves</div><div className="legend-item"><span className="legend-key">SV%:</span> Save Percentage</div></div></div></div>
        <div className="stats-update-message">Final Spring 2026 records · Read-only archive</div>
      </div>
    </main>
  );
}

function GameDetails({ gameId }: { gameId: string }) {
  const summary = summaries[gameId];
  const events = data.events.filter((event) => event.game_id === gameId && event.event_type === "goal");
  return <div className="game-card-back-content"><div className="game-card-stats-section"><div className="game-card-stats-title">Game Summary</div><table className="game-card-stats-table"><thead><tr><th>Shots</th><th>Goals</th><th>Scorers</th></tr></thead><tbody><tr><td>{summary ? `${summary.away_team_shots} – ${summary.home_team_shots}` : "—"}</td><td>{summary ? `${summary.away_team_score} – ${summary.home_team_score}` : "—"}</td><td>{events.length ? events.map((event) => players[event.player_id || ""]?.name).filter(Boolean).join(", ") : "No scorer detail"}</td></tr></tbody></table></div></div>;
}
