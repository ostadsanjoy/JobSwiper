import React, { useState } from "react";
import { updateApplicationStatus, EXPORT_CSV_URL } from "../api.js";

const STAGES = [
  { id: "applied", label: "📤 Applied", color: "#3b82f6" },
  { id: "interviewing", label: "💬 Interviewing", color: "#d97706" },
  { id: "offer", label: "🏆 Offer", color: "#059669" },
  { id: "rejected", label: "❌ Rejected", color: "#dc2626" },
];

export default function ApplicationsKanban({ history, onStatusChanged }) {
  const [movingId, setMovingId] = useState(null);

  const moveStatus = (jobId, nextStatus) => {
    setMovingId(jobId);
    updateApplicationStatus(jobId, nextStatus)
      .then(() => {
        if (onStatusChanged) onStatusChanged();
      })
      .finally(() => setMovingId(null));
  };

  const getStageApplications = (stageId) => {
    return history.filter((item) => {
      const st = (item.status || "applied").toLowerCase();
      if (stageId === "applied") return st === "applied" || st === "autofilled" || st === "saved";
      return st === stageId;
    });
  };

  return (
    <div className="kanban-wrapper">
      <div className="kanban-header">
        <h3 className="kanban-title">Pipeline Stage Tracker</h3>
        <a href={EXPORT_CSV_URL} download="job_applications.csv" className="export-csv-btn">
          📥 Export CSV
        </a>
      </div>

      <div className="kanban-board">
        {STAGES.map((stage) => {
          const apps = getStageApplications(stage.id);
          return (
            <div className="kanban-column" key={stage.id}>
              <div className="kanban-column-header" style={{ borderColor: stage.color }}>
                <span className="stage-label">{stage.label}</span>
                <span className="stage-count">{apps.length}</span>
              </div>

              <div className="kanban-column-body">
                {apps.map((app) => (
                  <div className="kanban-card" key={app.id}>
                    <div className="kanban-card-title">{app.title}</div>
                    <div className="kanban-card-company">{app.company}</div>
                    <div className="kanban-card-meta">
                      {app.location || "Remote"} &middot; {app.compensation || "Not specified"}
                    </div>

                    <div className="kanban-move-actions">
                      {STAGES.filter((s) => s.id !== stage.id).map((target) => (
                        <button
                          key={target.id}
                          className="move-chip"
                          disabled={movingId === app.id}
                          onClick={() => moveStatus(app.id, target.id)}
                        >
                          &rarr; {target.label.split(" ")[1]}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}

                {apps.length === 0 && <div className="kanban-empty">No applications</div>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
