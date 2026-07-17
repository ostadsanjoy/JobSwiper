import React from "react";
import { sanitizeHtml } from "../utils.js";

export default function JobDetailModal({ job, onClose }) {
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
        <div className="job-description job-description-full" dangerouslySetInnerHTML={{ __html: safeHtml }} />
        <div className="review-actions">
          <button className="approve-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}