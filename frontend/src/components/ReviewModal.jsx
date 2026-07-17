import React, { useState, useEffect } from "react";

export default function ReviewModal({ job, tailored, onApprove, onDiscard }) {
  const [resume, setResume] = useState(tailored.resume);
  const [coverLetter, setCoverLetter] = useState(tailored.cover_letter);

  useEffect(() => {
    setResume(tailored.resume);
    setCoverLetter(tailored.cover_letter);
  }, [tailored]);

  return (
    <div className="modal-backdrop">
      <div className="review-sheet">
        <h2>Review before applying: {job.title} @ {job.company}</h2>

        <div className="review-field">
          <label>Tailored resume</label>
          <textarea
            className="review-textarea"
            value={resume}
            onChange={(e) => setResume(e.target.value)}
          />
        </div>

        <div className="review-field">
          <label>Cover letter</label>
          <textarea
            className="review-textarea"
            value={coverLetter}
            onChange={(e) => setCoverLetter(e.target.value)}
          />
        </div>

        <div className="review-actions">
          <button className="discard-btn" onClick={onDiscard}>
            Discard, don't apply
          </button>
          <button
            className="approve-btn"
            onClick={() => onApprove({ resume, coverLetter })}
          >
            Looks good, autofill it
          </button>
        </div>
      </div>
    </div>
  );
}