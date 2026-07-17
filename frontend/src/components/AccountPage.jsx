import React, { useEffect, useState } from "react";
import ResumeUpload from "./ResumeUpload.jsx";
import { getCurrentResume, getHistory } from "../api.js";

function HistoryEntry({ entry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="history-entry">
      <div className="history-entry-header" onClick={() => setExpanded((e) => !e)}>
        <div>
          <strong>{entry.title}</strong> @ {entry.company}
        </div>
        <span className={`history-status ${entry.status}`}>{entry.status}</span>
      </div>
      <div className="history-entry-meta">
        {entry.location || "Location not listed"} &middot; {entry.compensation || "Not specified"} &middot;{" "}
        {new Date(entry.timestamp).toLocaleString()}
      </div>

      {expanded && (
        <div className="history-entry-detail">
          {entry.github_repos.length > 0 && (
            <div className="history-detail-block">
              <label>GitHub repos used for context</label>
              <div className="repo-chip-row">
                {entry.github_repos.map((r) => (
                  <span className="repo-chip" key={r}>{r}</span>
                ))}
              </div>
            </div>
          )}

          {entry.resume_text && (
            <div className="history-detail-block">
              <label>Generated resume</label>
              <pre className="history-text-block">{entry.resume_text}</pre>
            </div>
          )}

          {entry.cover_letter && (
            <div className="history-detail-block">
              <label>Cover letter</label>
              <pre className="history-text-block">{entry.cover_letter}</pre>
            </div>
          )}

          {entry.apply_url && (
            <a href={entry.apply_url} target="_blank" rel="noreferrer" className="history-apply-link">
              Original posting &rarr;
            </a>
          )}
        </div>
      )}
    </div>
  );
}
export default function AccountPage({ onResumeChange }) {
  const [resume, setResume] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    Promise.all([getCurrentResume(), getHistory()])
      .then(([resumeData, historyData]) => {
        setResume(resumeData);
        setHistory(historyData);
        if (onResumeChange) onResumeChange(resumeData);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="account-page">
      <div className="account-section">
        <h2 className="account-section-title">Resume on file</h2>
        <ResumeUpload currentResume={resume} onUploaded={refresh} />
      </div>

      <div className="account-section">
        <h2 className="account-section-title">Application history ({history.length})</h2>
        {loading && <p className="status-line">Loading...</p>}
        {!loading && history.length === 0 && (
          <p className="status-line">No applications yet - swipe right on something.</p>
        )}
        <div className="history-list">
          {history.map((entry) => (
            <HistoryEntry entry={entry} key={entry.id} />
          ))}
        </div>
      </div>
    </div>
  );
}