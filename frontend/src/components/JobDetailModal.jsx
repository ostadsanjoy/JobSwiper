import React from "react";
import { sanitizeHtml } from "../utils.js";

export default function JobDetailModal({ job, matchData, onClose }) {
  const safeHtml = sanitizeHtml(job.description);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="review-sheet" onClick={(e) => e.stopPropagation()}>
        <h2>{job.title} @ {job.company}</h2>
        <div className="job-location">{job.location || "Location not listed"}</div>
        <div className="job-detail-meta">
          <span>{job.remote_type || "unspecified"}</span>
          <span>{job.compensation || "Not specified"}</span>
        </div>

        {matchData && matchData.score > 0 && (
          <div className="ai-match-box">
            <div className="ai-match-header">
              <span className="ai-match-title">AI Fit Evaluation:</span>
              <span className="ai-match-score-badge">{matchData.score}% ({matchData.badge})</span>
            </div>
            <div className="ai-match-progress-bar">
              <div className="ai-match-progress-fill" style={{ width: `${matchData.score}%` }} />
            </div>

            {matchData.matching_skills?.length > 0 && (
              <div className="ai-skills-group">
                <span className="ai-skills-label">Matching Skills:</span>
                <div className="ai-skills-pills">
                  {matchData.matching_skills.map((s, i) => (
                    <span key={i} className="skill-pill match">✓ {s}</span>
                  ))}
                </div>
              </div>
            )}

            {matchData.missing_skills?.length > 0 && (
              <div className="ai-skills-group">
                <span className="ai-skills-label">Missing Skills:</span>
                <div className="ai-skills-pills">
                  {matchData.missing_skills.map((s, i) => (
                    <span key={i} className="skill-pill missing">! {s}</span>
                  ))}
                </div>
              </div>
            )}

            {matchData.portfolio_gaps?.length > 0 && (
              <div className="ai-skills-group" style={{ marginTop: 10 }}>
                <span className="ai-skills-label">Portfolio Gaps & Action Items:</span>
                <ul className="portfolio-gap-list">
                  {matchData.portfolio_gaps.map((gap, i) => (
                    <li key={i}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}

            {matchData.work_auth_fit && (
              <div className="ai-skills-group" style={{ marginTop: 8 }}>
                <span className="ai-skills-label">Work Auth & Sponsorship:</span>
                <span className="auth-fit-badge">🛡️ {matchData.work_auth_fit}</span>
              </div>
            )}
          </div>
        )}


        <div className="job-description job-description-full" dangerouslySetInnerHTML={{ __html: safeHtml }} />
        <div className="review-actions">
          <button className="approve-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}