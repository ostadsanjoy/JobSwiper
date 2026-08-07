import React, { useState, useEffect, useRef } from "react";
import { stripHtml } from "../utils.js";
import { getJobMatchScore } from "../api.js";
import JobDetailModal from "./JobDetailModal.jsx";

export default function JobCard({ job, onSwipe, stamp }) {
  const [showDetail, setShowDetail] = useState(false);
  const [matchData, setMatchData] = useState(null);
  const [dragX, setDragX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const startXRef = useRef(0);

  const previewText = stripHtml(job.description);

  useEffect(() => {
    if (job?.match_score !== undefined) {
      setMatchData({
        score: job.match_score,
        badge: job.match_badge || "Fit Score",
      });
    }
    if (job?.id) {
      getJobMatchScore(job.id)
        .then((res) => setMatchData(res))
        .catch(() => {});
    }
  }, [job?.id, job?.match_score, job?.match_badge]);


  const handleStart = (clientX) => {
    setIsDragging(true);
    startXRef.current = clientX;
  };

  const handleMove = (clientX) => {
    if (!isDragging) return;
    setDragX(clientX - startXRef.current);
  };

  const handleEnd = () => {
    if (!isDragging) return;
    setIsDragging(false);
    if (dragX > 120) {
      onSwipe("right");
    } else if (dragX < -120) {
      onSwipe("left");
    }
    setDragX(0);
  };

  const getScoreColorClass = (score) => {
    if (score >= 80) return "high-match";
    if (score >= 60) return "med-match";
    return "low-match";
  };

  return (
    <>
      <div
        className={`job-card ${isDragging ? "dragging" : ""}`}
        style={{
          transform: `translateX(${dragX}px) rotate(${dragX * 0.05}deg)`,
          transition: isDragging ? "none" : "transform 0.2s ease, opacity 0.2s ease",
          cursor: isDragging ? "grabbing" : "grab",
        }}
        onMouseDown={(e) => handleStart(e.clientX)}
        onMouseMove={(e) => handleMove(e.clientX)}
        onMouseUp={handleEnd}
        onMouseLeave={handleEnd}
        onTouchStart={(e) => handleStart(e.touches[0].clientX)}
        onTouchMove={(e) => handleMove(e.touches[0].clientX)}
        onTouchEnd={handleEnd}
      >
        <div className="card-tab">
          <span>{job.company}</span>
          <div className="card-tab-badges">
            {matchData && matchData.score > 0 && (
              <span className={`match-badge ${getScoreColorClass(matchData.score)}`}>
                ⚡ {matchData.score}% Match
              </span>
            )}
            <span className="remote-badge">{job.remote_type || "unspecified"}</span>
          </div>
        </div>

        <div className="card-body">
          <h2 className="job-title">{job.title}</h2>
          <div className="job-location">{job.location || "Location not listed"}</div>
          <div className="job-compensation">{job.compensation || "Not specified"}</div>
          <div className="job-description collapsed">{previewText}</div>
        </div>

        <div className="card-actions">
          <button className="stamp-button skip" onClick={() => onSwipe("left")}>
            Pass
          </button>
          <button className="info-star-button" onClick={() => setShowDetail(true)} title="View full details">
            &#9733;
          </button>
          <button className="stamp-button apply" onClick={() => onSwipe("right")}>
            Apply
          </button>
        </div>

        {stamp && (
          <div className="stamp-overlay stamp-fade">
            <div className={`stamp-overlay-text ${stamp}`}>
              {stamp === "applied" ? "APPLIED" : "PASSED"}
            </div>
          </div>
        )}
      </div>

      {showDetail && <JobDetailModal job={job} matchData={matchData} onClose={() => setShowDetail(false)} />}
    </>
  );
}