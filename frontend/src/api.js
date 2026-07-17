import axios from "axios";

const BASE_URL = "http://localhost:8000";

export const getJobs = ({ keywords = "", location = "", remoteType = "", country = "" } = {}) =>
  axios
    .get(`${BASE_URL}/jobs`, { params: { keywords, location, remote_type: remoteType, country } })
    .then((r) => r.data);

export const tailorJob = (jobId) =>
  axios.post(`${BASE_URL}/jobs/${jobId}/tailor`, {}).then((r) => r.data);

export const generateResumePdf = (jobId, resumeText) =>
  axios
    .post(`${BASE_URL}/jobs/${jobId}/resume-pdf`, { resume_text: resumeText })
    .then((r) => r.data);

export const autofillJob = (jobId, resumeText, coverLetter, resumePdfPath) =>
  axios
    .post(`${BASE_URL}/jobs/${jobId}/autofill`, {
      resume_text: resumeText,
      cover_letter: coverLetter,
      resume_pdf_path: resumePdfPath || "",
    })
    .then((r) => r.data);

export const logJob = (jobId, status, extra = {}) =>
  axios
    .post(`${BASE_URL}/jobs/${jobId}/log`, {
      status,
      resume_text: extra.resumeText || "",
      cover_letter: extra.coverLetter || "",
      github_repos: extra.githubRepos || [],
    })
    .then((r) => r.data);

export const uploadResume = (file) => {
  const form = new FormData();
  form.append("file", file);
  return axios
    .post(`${BASE_URL}/resume/upload`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const getCurrentResume = () =>
  axios.get(`${BASE_URL}/resume/current`).then((r) => r.data);

export const getHistory = () =>
  axios.get(`${BASE_URL}/history`).then((r) => r.data);