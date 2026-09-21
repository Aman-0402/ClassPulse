import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Table } from "react-bootstrap";
import { getOtpHistory, logout } from "../../api/client";
import type { OTPHistoryEntry } from "../../api/client";
import AppShell from "../../components/AppShell";
import PageHeader from "../../components/PageHeader";
import LoadingScreen from "../../components/LoadingScreen";
import { formatSessionTime } from "../../utils/time";

const STATUS_STAMP: Record<OTPHistoryEntry["status"], string> = {
  active: "stamp-present",
  used: "stamp-neutral",
  expired: "stamp-absent",
};

export default function OTPHistoryPage() {
  const [history, setHistory] = useState<OTPHistoryEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getOtpHistory()
      .then(setHistory)
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load OTP history.");
        }
      });
  }, [navigate]);

  if (!history && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Teacher"
        title="Password Reset OTP History"
        subtitle="Every OTP a student has requested. Active codes still work; used and expired ones stay for the audit trail. Confirm who they are before relaying a code."
      />
      {error && <Alert variant="danger">{error}</Alert>}
      {history && history.length === 0 && <p className="text-muted">No OTP requests yet.</p>}
      {history && history.length > 0 && (
        <div className="table-responsive">
          <Table striped bordered>
            <thead>
              <tr>
                <th>Student</th>
                <th>Username</th>
                <th>Code</th>
                <th>Requested</th>
                <th>Expires</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.full_name}</td>
                  <td className="font-mono">{entry.username}</td>
                  <td className="font-mono">{entry.code}</td>
                  <td className="text-muted">{formatSessionTime(entry.created_at)}</td>
                  <td className="text-muted">{formatSessionTime(entry.expires_at)}</td>
                  <td>
                    <span className={`stamp ${STATUS_STAMP[entry.status]}`}>{entry.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </AppShell>
  );
}
