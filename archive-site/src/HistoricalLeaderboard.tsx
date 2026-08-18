"use client";

import { useEffect, useMemo, useState } from "react";
import data from "./historical-data.json";

const n = (value?: string) => Number(value || 0);
const teams = Object.fromEntries(data.teams.map((team) => [team.id, team]));
const summaries = Object.fromEntries(data.summaries.map((summary) => [summary.game_id, summary]));
const players = Object.fromEntries(data.players.map((player) => [player.id, player]));
const goalies = Object.fromEntries(data.goalies.map((goalie) => [goalie.id, goalie]));
const logo = (teamName: string) => `./logos/${teamName.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "")}.png`;

function teamSlug(name: string) {
  return name.toLowerCase().replace(/\s+/g, "_");
}

function prettyDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value.slice(0, 10)}T12:00:00Z`));
}

function periodLabel(period?: string) {
  const labels: Record<string, string> = { "1": "1st", "2": "2nd", "3": "3rd", "4": "OT", "5": "SO" };
  return labels[period || ""] || (period ? `Period ${period}` : "Period unavailable");
}

function assistNames(details: string) {
  if (!details) return [];
  try {
    const parsed = JSON.parse(details) as { assists?: Array<number | string> };
    return (parsed.assists || []).map((id) => players[String(id)]?.name).filter(Boolean);
  } catch {
    return [];
  }
}

export function HistoricalLeaderboard() {
  const [teamId, setTeamId] = useState<string | null>(null);
  const [expandedGame, setExpandedGame] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => {
      const slug = window.location.hash.replace(/^#team\//, "");
      const team = data.teams.find((item) => teamSlug(item.name) === slug);
      setTeamId(team?.id || null);
      setExpandedGame(null);
      window.scrollTo(0, 0);
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const standings = useMemo(
    () => [...data.standings].sort((a, b) => n(b.points) - n(a.points) || n(b.wins) - n(a.wins)),
    [],
  );
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
            return <div className="standings-row" key={row.id}><div><img className="team-logo" src={logo(team.name)} alt={`${team.name} logo`} /></div><div className="team-name"><a href={`#team/${teamSlug(team.name)}`}>{team.name}</a></div><div>{row.games_played}</div><div>{row.wins}</div><div>{row.losses}</div><div>{row.ties}</div><div>{row.goals_scored}</div><div className="team-pts">{row.points}</div></div>;
          })}
        </div>
        <div className="standings-update-message">Final Spring 2026 standings · Read-only historical archive</div>
      </main>
    );
  }

  const teamGames = [...data.games]
    .filter((game) => game.home_team_id === teamId || game.away_team_id === teamId)
    .sort((a, b) => a.game_date.localeCompare(b.game_date));
  const skaters = data.playerStats
    .filter((stat) => stat.team_id === teamId)
    .map((stat) => ({ ...players[stat.player_id], ...stat }))
    .sort((a, b) => n(a.jersey_number) - n(b.jersey_number));
  const teamGoalies = data.goalieStats
    .filter((stat) => stat.team_id === teamId)
    .map((stat) => ({ ...goalies[stat.goalie_id], ...stat }));

  return (
    <main id="team-page" className="screen">
      <div className="app-header team-header">
        <div className="app-logo"><img src={logo(selectedTeam.name)} alt={`${selectedTeam.name} logo`} /></div>
        <h1 className="app-title">{selectedTeam.name}</h1>
        <a href="#" className="back-link">← Back to Standings</a>
      </div>
      <div className="schedule-container mobile-schedule">
        {teamGames.map((game) => (
          <GameCard
            key={game.id}
            game={game}
            selectedTeamId={teamId!}
            expanded={expandedGame === game.id}
            onToggle={() => setExpandedGame(expandedGame === game.id ? null : game.id)}
          />
        ))}
      </div>
      <div className="player-stats-container">
        <div className="player-stats-title">Player Stats</div>
        <table className="player-stats-table"><thead><tr><th>#</th><th>NAME</th><th>G</th><th>A</th><th>P</th></tr></thead><tbody>{skaters.map((player) => <tr key={player.id}><td>{player.jersey_number || "-"}</td><td className="player-name-cell">{player.name}</td><td>{player.goals}</td><td>{player.assists}</td><td>{player.points}</td></tr>)}</tbody></table>
        {teamGoalies.length > 0 && <div className="goalie-stats-container"><table className="player-stats-table goalie-stats-table"><thead><tr className="goalie-header-row"><th>#</th><th>Name</th><th>SA</th><th>GA</th><th>SV</th><th>SV%</th></tr></thead><tbody>{teamGoalies.map((goalie) => <tr className="goalie-row" key={goalie.id}><td>{goalie.jersey_number || "-"}</td><td>{goalie.name}</td><td>{goalie.shots_against}</td><td>{goalie.goals_allowed}</td><td>{goalie.saves}</td><td>{Number(goalie.save_percentage).toFixed(3)}</td></tr>)}</tbody></table></div>}
        <div className="stats-update-message">Final Spring 2026 records · Read-only archive</div>
      </div>
    </main>
  );
}

function GameCard({ game, selectedTeamId, expanded, onToggle }: {
  game: (typeof data.games)[number];
  selectedTeamId: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const summary = summaries[game.id];
  const selectedIsHome = game.home_team_id === selectedTeamId;
  const selected = teams[selectedTeamId];
  const opponent = teams[selectedIsHome ? game.away_team_id : game.home_team_id];
  const selectedScore = summary ? (selectedIsHome ? summary.home_team_score : summary.away_team_score) : "—";
  const opponentScore = summary ? (selectedIsHome ? summary.away_team_score : summary.home_team_score) : "—";
  const tied = summary?.game_outcome === "tie";
  const won = Boolean(summary && !tied && summary.winner_team_id === selectedTeamId);
  const result = tied ? "T" : won ? "W" : "L";
  const overtime = summary?.went_to_shootout === "t" ? "/SO" : summary?.went_to_overtime === "t" ? "/OT" : "";

  return (
    <section className={`archive-game-card ${expanded ? "is-expanded" : ""}`}>
      <div className="archive-game-date">Week {game.week} · {prettyDate(game.game_date)}</div>
      <button className="archive-scoreboard" onClick={onToggle} aria-expanded={expanded}>
        <TeamScore team={selected} score={selectedScore} winner={won} />
        <div className="archive-game-status"><span>FINAL{overtime}</span><b className={`schedule-result-badge ${result.toLowerCase()}`}>{result}</b><small>{expanded ? "Hide" : "Details"}</small></div>
        <TeamScore team={opponent} score={opponentScore} winner={Boolean(summary && !tied && !won)} />
      </button>
      {expanded && <GameDetails game={game} selectedTeamId={selectedTeamId} />}
    </section>
  );
}

function TeamScore({ team, score, winner }: { team: (typeof data.teams)[number]; score: string; winner: boolean }) {
  return <div className={`archive-team ${winner ? "winner" : ""}`}><img src={logo(team.name)} alt={`${team.name} logo`} /><span>{team.name}</span><strong>{score}</strong></div>;
}

function GameDetails({ game, selectedTeamId }: { game: (typeof data.games)[number]; selectedTeamId: string }) {
  const summary = summaries[game.id];
  const selectedIsHome = game.home_team_id === selectedTeamId;
  const selected = teams[selectedTeamId];
  const opponent = teams[selectedIsHome ? game.away_team_id : game.home_team_id];
  const goals = data.events.filter((event) => event.game_id === game.id && event.event_type === "goal");
  const selectedGoals = goals.filter((event) => players[event.player_id || ""]?.team_id === selectedTeamId);
  const opponentGoals = goals.filter((event) => players[event.player_id || ""]?.team_id === opponent.id);
  const selectedScore = Number(selectedIsHome ? summary?.home_team_score : summary?.away_team_score) || 0;
  const opponentScore = Number(selectedIsHome ? summary?.away_team_score : summary?.home_team_score) || 0;
  const selectedShots = selectedIsHome ? summary?.home_team_shots : summary?.away_team_shots;
  const opponentShots = selectedIsHome ? summary?.away_team_shots : summary?.home_team_shots;

  return (
    <div className="archive-game-details">
      <h2>Game Summary</h2>
      <div className="scoring-section">
        <h3>Scoring</h3>
        <ScoringTeam team={selected} goals={selectedGoals} officialGoals={selectedScore} />
        <ScoringTeam team={opponent} goals={opponentGoals} officialGoals={opponentScore} />
      </div>
      <div className="shots-section">
        <h3>Shots on Goal</h3>
        <div className="shot-row"><span><img src={logo(selected.name)} alt="" />{selected.name}</span><strong>{selectedShots ?? "—"}</strong></div>
        <div className="shot-row"><span><img src={logo(opponent.name)} alt="" />{opponent.name}</span><strong>{opponentShots ?? "—"}</strong></div>
      </div>
    </div>
  );
}

function ScoringTeam({ team, goals, officialGoals }: { team: (typeof data.teams)[number]; goals: Array<(typeof data.events)[number]>; officialGoals: number }) {
  const missingDetails = Math.max(0, officialGoals - goals.length);
  return (
    <div className="scoring-team">
      <div className="scoring-team-heading"><span><img src={logo(team.name)} alt="" />{team.name}</span><strong>{officialGoals}</strong></div>
      {goals.length ? goals.map((goal, index) => {
        const scorer = players[goal.player_id || ""];
        const assists = assistNames(goal.details);
        return <div className="goal-row" key={goal.id}><span className="goal-number">{index + 1}</span><div><strong>{scorer ? `${scorer.jersey_number ? `#${scorer.jersey_number} ` : ""}${scorer.name}` : "Scorer unavailable"}</strong>{assists.length > 0 && <small>Assists: {assists.join(", ")}</small>}</div><span className="goal-period">{periodLabel(goal.period)}</span></div>;
      }) : officialGoals > 0 ? null : <div className="no-scoring-detail">No goals</div>}
      {missingDetails > 0 && <div className="no-scoring-detail">{missingDetails} {missingDetails === 1 ? "scorer was" : "scorers were"} not preserved in the archive</div>}
    </div>
  );
}
