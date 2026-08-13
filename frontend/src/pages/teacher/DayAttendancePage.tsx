import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Card, Form, Spinner, Table } from "react-bootstrap";
import { getAnalytics, getDayAttendance, logout } from "../../api/client";
import type { DayAttendanceResponse } from "../../api/client";
import AppShell from "../../components/AppShell";
import { formatTime } from "../../utils/time";

function todayIsoDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
}

export default function DayAttendancePage() {
  const [sections, setSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [date, setDate] = useState(todayIsoDate());
  const [data, setData] = useState<DayAttendanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getAnalytics()
      .then((result) => {
        setSections(result.available_sections);
        if (result.available_sections.length > 0) {
          setSection(result.available_sections[0]);
        }
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        }
      });
  }, [navigate]);

  useEffect(() => {
    if (!section || !date) return;
    let active = true;
    setLoading(true);
    getDayAttendance(section, date)
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (!active) return;
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load attendance for this date.");
          setData(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [section, date, navigate]);

  return (
    <AppShell>
      <div className="d-flex justify-content-between align-items-end mb-4 flex-wrap gap-2">
        <h1 className="h3 mb-0">Day-wise Attendance</h1>
        <div className="d-flex gap-2 flex-wrap">
          <Form.Group controlId="day-section" style={{ minWidth: 180 }}>
            <Form.Label className="small text-muted mb-1">Section</Form.Label>
            <Form.Select value={section} onChange={(e) => setSection(e.target.value)}>
              {sections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group controlId="day-date" style={{ minWidth: 170 }}>
            <Form.Label className="small text-muted mb-1">Date</Form.Label>
            <Form.Control type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Form.Group>
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      {loading && <Spinner animation="border" />}

      {!loading && data && (
        <>
          <Card className="mb-4" style={{ maxWidth: 480 }}>
            <Card.Body className="d-flex justify-content-between align-items-center">
              <div>
                <div className="text-muted small">Present</div>
                <div className="fs-4 font-mono">
                  {data.present_count} / {data.total_students}
                </div>
              </div>
              {data.sessions.length === 0 ? (
                <span className="stamp stamp-neutral">No session this day</span>
              ) : (
                <span className="stamp stamp-neutral">
                  {data.sessions.map((s) => formatTime(s.start_time)).join(", ")}
                </span>
              )}
            </Card.Body>
          </Card>

          {data.students.length === 0 ? (
            <p className="text-muted">No students in this section.</p>
          ) : (
            <Table striped bordered>
              <thead>
                <tr>
                  <th>S.No</th>
                  <th>CRN</th>
                  <th>Roll No.</th>
                  <th>Name</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.students.map((s, index) => (
                  <tr key={s.crn}>
                    <td>{index + 1}</td>
                    <td className="font-mono">{s.crn}</td>
                    <td className="font-mono">{s.roll_number}</td>
                    <td>{s.name}</td>
                    <td>
                      <span className={`stamp ${s.present ? "stamp-present" : "stamp-absent"}`}>
                        {s.present ? "Present" : "Absent"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </>
      )}
    </AppShell>
  );
}
