import React, { useEffect, useState } from "react";
import JobCard from "./components/JobCard.jsx";
import SearchBar from "./components/SearchBar.jsx";
import ReviewModal from "./components/ReviewModal.jsx";
import AccountPage from "./components/AccountPage.jsx";
import { getJobs, tailorJob, autofillJob, logJob, getCurrentResume } from "./api.js";

export default function App() {
  const [tab, setTab] = useState("swipe");
  const [jobs, setJobs] = useState([]);
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState("");
  const [stamp, setStamp] = useState(null);
  const [reviewData, setReviewData] = useState(null);
  const [hasResume, setHasResume] = useState(null);

  const currentJob = jobs[index];

  const runSearch = ({ keywords, location, country, remoteType }) => {
    setStatus("Searching...");
    getJobs({ keywords, location, country, remoteType })
      .then((data) => {
        setJobs(data);
        setIndex(0);
        setStatus(data.length ? "" : "No jobs matched that search.");
      })
      .catch(() => setStatus("Failed to load jobs."));
  };

  useEffect(() => {
    runSearch({});
    getCurrentResume().then((r) => setHasResume(Boolean(r.resume_text)));
  }, []);

  useEffect(() => {
    if (tab === "swipe") {
      getCurrentResume().then((r) => setHasResume(Boolean(r.resume_text)));
    }
  }, [tab]);

  const advance = (stampType) => {
    setStamp(stampType);
    setTimeout(() => {
      setStamp(null);
      setIndex((i) => i + 1);
    }, 550);
  };

  const handleSwipe = async (direction) => {
    if (!currentJob) return;

    if (direction === "left") {
      await logJob(currentJob.id, "skipped");
      advance("skipped");
      return;
    }

    if (!hasResume) {
      setStatus("Upload a resume in the Account tab before applying.");
      return;
    }

    setStatus(`Tailoring resume for ${currentJob.title}...`);
    try {
      const tailored = await tailorJob(currentJob.id);
      setStatus("");
      setReviewData(tailored);
    } catch (err) {
      const detail = err.response?.data?.detail || "Unknown error while tailoring.";
      setStatus(`Tailoring failed: ${detail}`);
    }
  };

  const handleApprove = async ({ resume, coverLetter, pdfPath }) => {
    const githubRepos = reviewData.github_repos || [];
    setReviewData(null);

    setStatus(`Opening application and autofilling ${currentJob.title}...`);
    try {
      const result = await autofillJob(currentJob.id, resume, coverLetter, pdfPath);
      await logJob(currentJob.id, "applied", { resumeText: resume, coverLetter, githubRepos });
      setStatus(
        `Autofilled ${result.filled_fields.length} field(s) across ${result.frames_considered} candidate frame(s) ` +
          `(${result.frames_skipped_as_thirdparty} third-party frame(s) skipped). ` +
          `${result.needs_manual_attention.length} field(s) need manual attention. ` +
          `Review the browser window, then submit.`
      );
      advance("applied");
    } catch (err) {
      setStatus("Autofill failed - check the backend logs.");
      advance("applied");
    }
  };

  const handleDiscard = async () => {
    setReviewData(null);
    await logJob(currentJob.id, "skipped");
    advance("skipped");
  };

  return (
    <div className="app-shell">
      <div className="app-title">Job Swiper</div>

      <div className="nav-tabs">
        <button className={`nav-tab ${tab === "swipe" ? "active" : ""}`} onClick={() => setTab("swipe")}>
          Swipe
        </button>
        <button className={`nav-tab ${tab === "account" ? "active" : ""}`} onClick={() => setTab("account")}>
          Account
        </button>
      </div>

      {tab === "swipe" ? (
        <>
          <SearchBar onSearch={runSearch} />

          {hasResume === false && (
            <p className="status-line resume-warning">
              No resume on file yet - you can still browse and skip, but swiping right needs a resume
              uploaded in the Account tab first.
            </p>
          )}

          <div className="card-stack">
            {currentJob ? (
              <JobCard job={currentJob} onSwipe={handleSwipe} stamp={stamp} />
            ) : (
              <div className="empty-state">No more jobs in the queue. Search again to fetch more.</div>
            )}
          </div>

          {status && <p className="status-line">{status}</p>}

          {reviewData && currentJob && (
            <ReviewModal job={currentJob} tailored={reviewData} onApprove={handleApprove} onDiscard={handleDiscard} />
          )}
        </>
      ) : (
        <AccountPage onResumeChange={(r) => setHasResume(Boolean(r.resume_text))} />
      )}
    </div>
  );
}