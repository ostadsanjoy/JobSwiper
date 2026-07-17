import React, { useState } from "react";
import { uploadResume } from "../api.js";

export default function ResumeUpload({ currentResume, onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError("");
    try {
      const result = await uploadResume(file);
      onUploaded(result);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  return (
    <div className="resume-upload">
      <label className="resume-upload-label">
        {currentResume?.source_filename
          ? `On file: ${currentResume.source_filename}`
          : "No resume uploaded yet"}
      </label>
      <input
        type="file"
        accept="application/pdf"
        onChange={handleFile}
        disabled={uploading}
      />
      {uploading && <span className="resume-upload-status">Extracting text...</span>}
      {error && <span className="resume-upload-error">{error}</span>}
    </div>
  );
}