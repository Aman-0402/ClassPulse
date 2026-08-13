import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Spinner, Table } from "react-bootstrap";
import { ATTENDANCE_THRESHOLD, getStudentHistory, logout } from "../../api/client";
import type { AttendanceHistoryResponse } from "../../api/client";
import AppShell from "../../components/AppShell";

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
        <Spinner animation="border" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="h3 mb-4">Attendance History</h1>
      <Card className="mb-4" style={{ maxWidth: 480 }}>
        <Card.Body className="d-flex justify-content-between align-items-center">
          <div>
            <div className="text-muted small">Total Classes</div>
            <div className="fs-4 font-mono">{data.total}</div>
          </div>
          <div>
            <div className="text-muted small">Present</div>
            <div className="fs-4 font-mono">{data.present}</div>
          </div>
          <span className={`stamp ${data.percentage >= ATTENDANCE_THRESHOLD ? "stamp-present" : "stamp-absent"}`}>
            {data.percentage}%
          </span>
        </Card.Body>
      </Card>

      {data.history.length === 0 ? (
        <p className="text-muted">No classes recorded yet — history appears here once a session closes.</p>
      ) : (
        <Table striped bordered>
          <thead>
            <tr>
              <th>Date</th>
              <th>Subject</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.history.map((entry, index) => (
              <tr key={`${entry.date}-${index}`}>
                <td className="font-mono">{entry.date}</td>
                <td>{entry.subject}</td>
                <td>
                  <span className={`stamp ${entry.status === "present" ? "stamp-present" : "stamp-absent"}`}>
                    {entry.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </AppShell>
  );
}
