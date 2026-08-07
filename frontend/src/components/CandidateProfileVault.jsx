import React, { useState, useEffect } from "react";
import { getProfile, saveProfile } from "../api.js";

export default function CandidateProfileVault() {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    location: "",
    linkedin_url: "",
    github_url: "",
    portfolio_url: "",
    work_auth: "Authorized to work",
    sponsorship_req: "No sponsorship required",
    expected_salary: "Open / Market Rate",
    notice_period: "Immediate / 2 Weeks",
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getProfile().then((data) => {
      if (data) setForm((prev) => ({ ...prev, ...data }));
    });
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    saveProfile(form)
      .then(() => setMsg("Profile facts saved! AI Agent will use these for ground truth autofill."))
      .catch(() => setMsg("Failed to save profile."))
      .finally(() => setSaving(false));
  };

  return (
    <div className="profile-vault-card">
      <form onSubmit={handleSave}>
        <div className="vault-grid">
          <div className="vault-field">
            <label>Full Name</label>
            <input type="text" name="full_name" value={form.full_name || ""} onChange={handleChange} placeholder="e.g. Jane Doe" />
          </div>

          <div className="vault-field">
            <label>Email Address</label>
            <input type="email" name="email" value={form.email || ""} onChange={handleChange} placeholder="jane.doe@example.com" />
          </div>

          <div className="vault-field">
            <label>Phone Number</label>
            <input type="text" name="phone" value={form.phone || ""} onChange={handleChange} placeholder="+1 (555) 000-0000" />
          </div>

          <div className="vault-field">
            <label>Current Location</label>
            <input type="text" name="location" value={form.location || ""} onChange={handleChange} placeholder="San Francisco, CA / Remote" />
          </div>

          <div className="vault-field">
            <label>Work Authorization</label>
            <input type="text" name="work_auth" value={form.work_auth || ""} onChange={handleChange} placeholder="e.g. Authorized to work in US" />
          </div>

          <div className="vault-field">
            <label>Visa Sponsorship Needs</label>
            <input type="text" name="sponsorship_req" value={form.sponsorship_req || ""} onChange={handleChange} placeholder="e.g. No sponsorship required" />
          </div>

          <div className="vault-field">
            <label>Expected Salary</label>
            <input type="text" name="expected_salary" value={form.expected_salary || ""} onChange={handleChange} placeholder="e.g. $120,000 - $140,000" />
          </div>

          <div className="vault-field">
            <label>Notice Period / Availability</label>
            <input type="text" name="notice_period" value={form.notice_period || ""} onChange={handleChange} placeholder="e.g. Immediate / 2 Weeks" />
          </div>

          <div className="vault-field">
            <label>LinkedIn URL</label>
            <input type="url" name="linkedin_url" value={form.linkedin_url || ""} onChange={handleChange} placeholder="https://linkedin.com/in/username" />
          </div>

          <div className="vault-field">
            <label>GitHub URL</label>
            <input type="url" name="github_url" value={form.github_url || ""} onChange={handleChange} placeholder="https://github.com/username" />
          </div>

          <div className="vault-field full-width">
            <label>Portfolio / Personal Website</label>
            <input type="url" name="portfolio_url" value={form.portfolio_url || ""} onChange={handleChange} placeholder="https://myportfolio.com" />
          </div>
        </div>

        <div className="vault-actions">
          <button type="submit" className="save-vault-btn" disabled={saving}>
            {saving ? "Saving..." : "Save Profile Facts"}
          </button>
          {msg && <span className="vault-msg">{msg}</span>}
        </div>
      </form>
    </div>
  );
}
