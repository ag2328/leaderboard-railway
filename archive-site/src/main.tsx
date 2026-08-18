import React from "react";
import ReactDOM from "react-dom/client";
import { HistoricalLeaderboard } from "./HistoricalLeaderboard";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HistoricalLeaderboard />
  </React.StrictMode>,
);
