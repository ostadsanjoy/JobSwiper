import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { stripHtml } from "../utils.js";
import JobDetailModal from "./JobDetailModal.jsx";

export default function JobCard({ job, onSwipe, stamp }) {
  const [showDetail, setShowDetail] = useState(false);
  const previewText = stripHtml(job.description);

  return (
    <>
      <motion.div
        className="job-card"
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        onDragEnd={(_, info) => {
          if (info.offset.x > 120) onSwipe("right");
          else if (info.offset.x < -120) onSwipe("left");
        }}
        whileDrag={{ scale: 1.03 }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <div className="card-tab">
          <span>{job.company}</span>
          <span className="remote-badge">{job.remote_type || "unspecified"}</span>
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

        <AnimatePresence>
          {stamp && (
            <motion.div
              className="stamp-overlay"
              initial={{ opacity: 0, scale: 1.4 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              <div className={`stamp-overlay-text ${stamp}`}>
                {stamp === "applied" ? "APPLIED" : "PASSED"}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {showDetail && <JobDetailModal job={job} onClose={() => setShowDetail(false)} />}
    </>
  );
}