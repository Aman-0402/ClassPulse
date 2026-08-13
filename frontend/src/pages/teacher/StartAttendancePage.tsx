import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Form, Button, Alert } from "react-bootstrap";
import { getCurrentSchedule, startSession } from "../../api/client";
import AppShell from "../../components/AppShell";

const DURATION_OPTIONS = [5, 10, 15, 30, 60];

export default function StartAttendancePage() {
  const [subject, setSubject] = useState("");
  const [duration, setDuration] = useState(5);
  const [merged, setMerged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scheduleHint, setScheduleHint] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getCurrentSchedule()
      .then((data) => {
        if (data.matched && data.subject && data.section) {
          const label = `${data.subject} — BBA III ${data.section}`;
          setSubject(label);
          setScheduleHint(`Auto-filled from today's timetable: ${label}`);
        }
      })
      .catch(() => {
        // Timetable auto-fill is a convenience, not required — the form still works blank.
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const session = await startSession(subject, duration, merged ? 2 : 1);
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
              <Form.Control value={subject} onChange={(e) => setSubject(e.target.value)} required />
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
