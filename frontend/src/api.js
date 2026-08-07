const BASE_URL = "http://localhost:8000";

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = `HTTP Error ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch (_) {}
    const error = new Error(detail);
    error.response = { data: { detail } };
    throw error;
  }
  return res.json();
}

export const getJobs = ({ keywords = "", location = "", remoteType = "", country = "" } = {}) => {
  const params = new URLSearchParams();
  if (keywords) params.append("keywords", keywords);
  if (location) params.append("location", location);
  if (remoteType) params.append("remote_type", remoteType);
  if (country) params.append("country", country);
  const query = params.toString() ? `?${params.toString()}` : "";
  return request(`${BASE_URL}/jobs${query}`);
};

export const tailorJob = (jobId) =>
  request(`${BASE_URL}/jobs/${jobId}/tailor`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });

export const generateResumePdf = (jobId, resumeText) =>
  request(`${BASE_URL}/jobs/${jobId}/resume-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_text: resumeText }),
  });

export const getResumePdfPreviewUrl = (jobId) =>
  `${BASE_URL}/jobs/${jobId}/resume-pdf/file?t=${Date.now()}`;

export const autofillJob = (jobId, resumeText, coverLetter, resumePdfPath) =>
  request(`${BASE_URL}/jobs/${jobId}/autofill`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resume_text: resumeText,
      cover_letter: coverLetter,
      resume_pdf_path: resumePdfPath || "",
    }),
  });

export const logJob = (jobId, status, extra = {}) =>
  request(`${BASE_URL}/jobs/${jobId}/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status,
      resume_text: extra.resumeText || "",
      cover_letter: extra.coverLetter || "",
      github_repos: extra.githubRepos || [],
    }),
  });

export const uploadResume = (file) => {
  const form = new FormData();
  form.append("file", file);
  return request(`${BASE_URL}/resume/upload`, {
    method: "POST",
    body: form,
  });
};

export const getCurrentResume = () => request(`${BASE_URL}/resume/current`);

export const getHistory = () => request(`${BASE_URL}/history`);

export const getJobMatchScore = (jobId) => request(`${BASE_URL}/jobs/${jobId}/match`);

export const getPortfolioAudit = () => request(`${BASE_URL}/account/audit`);

export const getProfile = () => request(`${BASE_URL}/profile`);

export const saveProfile = (data) =>
  request(`${BASE_URL}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

export const updateApplicationStatus = (jobId, status) =>
  request(`${BASE_URL}/applications/${jobId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });

export const EXPORT_CSV_URL = `${BASE_URL}/applications/export`;