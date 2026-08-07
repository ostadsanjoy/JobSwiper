import React, { useState } from "react";

const COUNTRIES = [
  { code: "", label: "Any Adzuna country" },
  { code: "us", label: "United States" },
  { code: "in", label: "India" },
  { code: "gb", label: "United Kingdom" },
  { code: "au", label: "Australia" },
  { code: "de", label: "Germany" },
  { code: "fr", label: "France" },
  { code: "ca", label: "Canada" },
  { code: "nz", label: "New Zealand" },
];

const REMOTE_TYPES = [
  { value: "", label: "Any" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "Onsite" },
];

export default function SearchBar({ onSearch }) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [country, setCountry] = useState("");
  const [remoteType, setRemoteType] = useState("");

  const runSearch = () => onSearch({ keywords, location, country, remoteType });

  return (
    <div className="search-bar">
      <div className="search-row">
        <input
          className="search-input"
          placeholder="role, skill, keyword..."
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
        />
        <button className="search-button" onClick={runSearch}>
          Search
        </button>
      </div>

      <div className="search-row">
        <input
          className="search-input"
          placeholder="city, region, or 'remote' - type anything"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
        />
        <select
          className="search-select"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
        >
          {COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div className="pill-row">
        {REMOTE_TYPES.map((r) => (
          <button
            key={r.value}
            className={`pill ${remoteType === r.value ? "active" : ""}`}
            onClick={() => {
              setRemoteType(r.value);
              onSearch({ keywords, location, country, remoteType: r.value });
            }}
          >
            {r.label}
          </button>
        ))}
      </div>
    </div>
  );
}