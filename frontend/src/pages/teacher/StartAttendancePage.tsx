import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Card, Form, Button, Alert } from "react-bootstrap";
import { getCurrentSchedule, startSession } from "../../api/client";
import AppShell from "../../components/AppShell";

const SUBJECT = "AI Training";
const DURATION_OPTIONS = [5, 10, 15, 30, 60];

interface PrefillState {
  subject: string;
  section: string;
  periods: number;
}

export default function StartAttendancePage() {
  const location = useLocation();
  const prefill = location.state as PrefillState | null;

  const [section, setSection] = useState(prefill?.section ?? "");
  const [duration, setDuration] = useState(5);
  const [merged, setMerged] = useState(prefill?.periods === 2);
  const [error, setError] = useState<string | null>(null);
  const [scheduleHint, setScheduleHint] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (prefill) {
      setScheduleHint(`From today's timetable: BBA III ${prefill.section}`);
      return;
    }
    getCurrentSchedule()
      .then((data) => {
        if (data.matched && data.section) {
          setSection(data.section);
          setScheduleHint(`Auto-filled from today's timetable: BBA III ${data.section}`);
        }
      })
      .catch(() => {
        // Timetable auto-fill is a convenience, not required — the form still works blank.
      });
    // Only re-run when this page is opened without a specific slot pre-filled.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const session = await startSession(SUBJECT, duration, merged ? 2 : 1, section);
      navigate(`/teacher/session/${session.id}`);
    } catch {
      setError("Could not start attendance session.");
    }
  };

  return (
    <AppShell>
      <h1 className="h3 mb-4">Start Attendance</h1>
      <Card style={{ maxWidth: 400 }}>
        <Card.Body>
          {error && <Alert variant="danger">{error}</Alert>}
          {scheduleHint && <Alert variant="info">{scheduleHint}</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="subject">
              <Form.Label>Subject</Form.Label>
              <Form.Control value={SUBJECT} disabled readOnly />
            </Form.Group>
            <Form.Group className="mb-3" controlId="duration">
              <Form.Label>Attendance window</Form.Label>
              <Form.Select value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                {DURATION_OPTIONS.map((minutes) => (
                  <option key={minutes} value={minutes}>
                    {minutes} minutes
                  </option>
                ))}
              </Form.Select>
              <Form.Text className="text-muted">
                Students can mark attendance until this window closes.
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3" controlId="merged">
              <Form.Check
                type="checkbox"
                label="Merge with next continuous period (double period)"
                checked={merged}
                onChange={(e) => setMerged(e.target.checked)}
              />
              <Form.Text className="text-muted">
                One QR scan marks attendance for both periods, and it counts as 2 sessions in
                reports.
              </Form.Text>
            </Form.Group>
            <Button type="submit" className="w-100">
              Start Session
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </AppShell>
  );
}
