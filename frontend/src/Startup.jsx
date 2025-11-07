import { useState } from "react";

const companies = [
  { code: "RIL_CONSOLIDATED", name: "Reliance Industries (Consolidated)" },
  // later: add JIO_PLATFORMS, RELIANCE_RETAIL, etc.
];

const roles = ["Analyst", "CEO", "Group Management"];

export default function Startup({ onStart }) {
  const [selectedCompany, setSelectedCompany] = useState(companies[0].code);
  const [selectedRole, setSelectedRole] = useState(roles[0]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const c = companies.find((c) => c.code === selectedCompany);
    onStart(c.code, c.name, selectedRole);
  };

  return (
    <div style={{ maxWidth: 480, margin: "40px auto", padding: 16 }}>
      <h1>Balance Sheet Chat</h1>
      <p>Select your company and role to start.</p>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 12 }}>
          <label>Company</label>
          <br />
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
          >
            {companies.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 12 }}>
          <label>Role</label>
          <br />
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
          >
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <button type="submit">Start Analysis</button>
      </form>
    </div>
  );
}
