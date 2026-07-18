import React, { useState, useEffect } from "react";
import { generateResumePdf, getResumePdfPreviewUrl } from "../api.js";

export default function ReviewModal({ job, tailored, onApprove, onDiscard }) {
  const [resume, setResume] = useState(tailored.resume);
  const [coverLetter, setCoverLetter] = useState(tailored.cover_letter);
  const [pdfPath, setPdfPath] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [usedFallback, setUsedFallback] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setResume(tailored.resume);
    setCoverLetter(tailored.cover_letter);
    setPdfPath(null);
    setPreviewUrl(null);
    setError("");
  }, [tailored]);

  const handleGeneratePdf = async () => {
    setGenerating(true);
    setError("");
    try {
      const result = await generateResumePdf(job.id, resume);
      setPdfPath(result.pdf_path);
      setUsedFallback(result.used_fallback_template);
      setPreviewUrl(getResumePdfPreviewUrl(job.id));
    } catch (err) {
      setError(err.response?.data?.detail || "PDF generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="review-sheet">
        <h2>Review before applying: {job.title} @ {job.company}</h2>

        <div className="review-field">
          <label>Tailored resume</label>
          <textarea
            className="review-textarea"
            value={resume}
            onChange={(e) => {
              setResume(e.target.value);
              setPdfPath(null);
              setPreviewUrl(null);
            }}
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

        <div className="pdf-generate-row">
          <button className="pdf-generate-btn" onClick={handleGeneratePdf} disabled={generating}>
            {generating ? "Generating PDF..." : previewUrl ? "Regenerate PDF" : "Generate PDF"}
          </button>
          {usedFallback && (
            <span className="pdf-fallback-note">
              Gemini's LaTeX didn't compile cleanly - used the safe backup template instead.
            </span>
          )}
          {error && <span className="resume-upload-error">{error}</span>}
        </div>

        {previewUrl && (
          <div className="pdf-preview-wrap">
            <label>PDF preview</label>
            <iframe title="Resume PDF preview" src={previewUrl} className="pdf-preview-frame" />
          </div>
        )}

        <div className="review-actions">
          <button className="discard-btn" onClick={onDiscard}>
            Discard, don't apply
          </button>
          <button
            className="approve-btn"
            disabled={!pdfPath}
            title={!pdfPath ? "Generate a PDF first" : ""}
            onClick={() => onApprove({ resume, coverLetter, pdfPath })}
          >
            Looks good, autofill it
          </button>
        </div>
      </div>
    </div>
  );
}