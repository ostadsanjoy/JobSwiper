import React, { useEffect, useState } from "react";
import ResumeUpload from "./ResumeUpload.jsx";
import CandidateProfileVault from "./CandidateProfileVault.jsx";
import { getCurrentResume, getHistory, getPortfolioAudit } from "../api.js";

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
          {entry.github_repos?.length > 0 && (
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
  const [audit, setAudit] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);
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

  const runAudit = () => {
    setAuditLoading(true);
    getPortfolioAudit()
      .then((data) => setAudit(data))
      .finally(() => setAuditLoading(false));
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="account-page">
      <div className="account-section">
        <h2 className="account-section-title">Candidate Q&A Vault & Profile Facts</h2>
        <CandidateProfileVault />
      </div>

      <div className="account-section">
        <h2 className="account-section-title">Resume on file</h2>
        <ResumeUpload currentResume={resume} onUploaded={refresh} />
      </div>

      <div className="account-section">
        <div className="account-section-header">
          <h2 className="account-section-title">GitHub Portfolio & Career Gap Analysis</h2>
          <button className="audit-btn" onClick={runAudit} disabled={auditLoading}>
            {auditLoading ? "Analyzing Portfolio..." : audit ? "Refresh AI Audit" : "Run AI Portfolio Audit"}
          </button>
        </div>

        {audit && (
          <div className="audit-card">
            <p className="audit-verdict">{audit.summary_verdict}</p>

            {audit.strengths?.length > 0 && (
              <div className="audit-group">
                <h4 className="audit-group-title strengths">🟢 Key Strengths</h4>
                <ul>
                  {audit.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {audit.critical_gaps?.length > 0 && (
              <div className="audit-group">
                <h4 className="audit-group-title gaps">🔴 Critical Portfolio Gaps</h4>
                <ul>
                  {audit.critical_gaps.map((g, i) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </div>
            )}

            {audit.immediate_focus?.length > 0 && (
              <div className="audit-group">
                <h4 className="audit-group-title focus">⚡ Immediate Action Recommendations</h4>
                <ul className="focus-list">
                  {audit.immediate_focus.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
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