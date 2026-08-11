import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Form, Button, Alert } from "react-bootstrap";
import { startSession } from "../../api/client";

export default function StartAttendancePage() {
  const [subject, setSubject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const session = await startSession(subject);
      navigate(`/teacher/session/${session.id}`);
    } catch {
      setError("Could not start attendance session.");
    }
  };

  return (
    <Container className="py-4" style={{ maxWidth: 400 }}>
      <h2>Start Attendance</h2>
      {error && <Alert variant="danger">{error}</Alert>}
      <Form onSubmit={handleSubmit}>
        <Form.Group className="mb-3" controlId="subject">
          <Form.Label>Subject</Form.Label>
          <Form.Control value={subject} onChange={(e) => setSubject(e.target.value)} required />
        </Form.Group>
        <Button type="submit">Start</Button>
      </Form>
    </Container>
  );
}
