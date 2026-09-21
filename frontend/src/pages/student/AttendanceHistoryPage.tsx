import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ATTENDANCE_THRESHOLD, getStudentHistory, logout } from "../../api/client";
import type { AttendanceHistoryResponse } from "../../api/client";
import AppShell from "../../components/AppShell";
import PageHeader from "../../components/PageHeader";
import LoadingScreen from "../../components/LoadingScreen";

export default function AttendanceHistoryPage() {
  const [data, setData] = useState<AttendanceHistoryResponse | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getStudentHistory()
      .then(setData)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  if (!data) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  const good = data.percentage >= ATTENDANCE_THRESHOLD;
  const absent = data.total - data.present;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Student"
        title="Attendance History"
        subtitle="Every closed class, newest first."
      />

      <section className="hist-stats">
        <div className={`hist-ring ${good ? "hist-ring-good" : "hist-ring-bad"}`}>
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <circle className="hist-ring-track" cx="60" cy="60" r="52" />
            <circle
              className="hist-ring-bar"
              cx="60"
              cy="60"
              r="52"
              strokeDasharray={`${(Math.min(data.percentage, 100) / 100) * 326.7} 326.7`}
            />
          </svg>
          <div className="hist-ring-text">
            <strong>{data.percentage}%</strong>
            <span>{good ? "On track" : `Below ${ATTENDANCE_THRESHOLD}%`}</span>
          </div>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Total classes</span>
          <span className="stat-value">{data.total}</span>
        </div>
        <div className="stat-tile stat-tile-good">
          <span className="stat-label">Present</span>
          <span className="stat-value">{data.present}</span>
        </div>
        <div className="stat-tile stat-tile-bad">
          <span className="stat-label">Absent</span>
          <span className="stat-value">{absent}</span>
        </div>
      </section>

      {data.history.length === 0 ? (
        <div className="empty-state">No classes recorded yet — history appears here once a session closes.</div>
      ) : (
        <>
          <div className="data-table-wrap d-none d-md-block">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Subject</th>
                  <th className="text-end">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.history.map((entry, index) => (
                  <tr key={`${entry.date}-${index}`}>
                    <td className="font-mono">{entry.date}</td>
                    <td>{entry.subject}</td>
                    <td className="text-end">
                      <span className={`stamp ${entry.status === "present" ? "stamp-present" : "stamp-absent"}`}>
                        {entry.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="hist-list d-md-none">
            {data.history.map((entry, index) => (
              <li key={`${entry.date}-${index}`} className={`hist-item hist-item-${entry.status}`}>
                <div>
                  <div className="font-mono small text-muted">{entry.date}</div>
                  <div className="fw-semibold">{entry.subject}</div>
                </div>
                <span className={`stamp ${entry.status === "present" ? "stamp-present" : "stamp-absent"}`}>
                  {entry.status}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </AppShell>
  );
}
