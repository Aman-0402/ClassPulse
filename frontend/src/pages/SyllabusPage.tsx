import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Form, Modal } from "react-bootstrap";
import {
  deleteSyllabusSession,
  getSyllabus,
  logout,
  saveSyllabusSession,
} from "../api/client";
import type { SyllabusSession, SyllabusSessionInput } from "../api/client";
import AppShell from "../components/AppShell";
import LoadingScreen from "../components/LoadingScreen";
import PageHeader from "../components/PageHeader";
import { confirmAction, notifyError, notifySuccess } from "../utils/alerts";

function nextSessionNumber(sessions: SyllabusSession[]): number {
  return sessions.length === 0 ? 1 : Math.max(...sessions.map((s) => s.session_number)) + 1;
}

function firstError(data: any): string {
  if (!data) return "Could not save this session.";
  if (typeof data.detail === "string") return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? String(first[0]) : String(first ?? "Could not save this session.");
}

// Shown to both roles — the course TOC/syllabus. Only a teacher/admin gets
// the add/edit/delete controls; a student sees the same list read-only.
export default function SyllabusPage() {
  const [sessions, setSessions] = useState<SyllabusSession[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<SyllabusSession | "new" | null>(null);
  const [form, setForm] = useState<SyllabusSessionInput>({ session_number: 1, topics: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const isTeacher = localStorage.getItem("classpulse_role") === "teacher";

  const load = () => {
    getSyllabus()
      .then((result) => {
        setSessions(result);
        setError(null);
      })
      .catch((err) => {
        if (err?.response?.status === 401) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load the syllabus.");
        }
      });
  };

  useEffect(load, [navigate]);

  const openNew = () => {
    setForm({ session_number: nextSessionNumber(sessions ?? []), topics: "" });
    setFormError(null);
    setEditing("new");
  };

  const openEdit = (session: SyllabusSession) => {
    setForm({ session_number: session.session_number, topics: session.topics });
    setFormError(null);
    setEditing(session);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await saveSyllabusSession(form, editing !== "new" && editing ? editing.id : undefined);
      setEditing(null);
      load();
      notifySuccess("Saved", "The syllabus has been updated.");
    } catch (err: any) {
      setFormError(firstError(err?.response?.data));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (session: SyllabusSession) => {
    const ok = await confirmAction(
      "Delete this session?",
      `Session ${session.session_number}: ${session.topics}`,
      "Delete"
    );
    if (!ok) return;
    try {
      await deleteSyllabusSession(session.id);
      load();
    } catch {
      notifyError("Delete Failed", "Could not delete that session.");
    }
  };

  if (!sessions && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow={isTeacher ? "Admin" : "Student"}
        title="Course Syllabus"
        subtitle="Session-wise topics covered in this course."
        actions={isTeacher ? <Button onClick={openNew}>+ Add session</Button> : undefined}
      />

      {error && <Alert variant="danger">{error}</Alert>}

      {sessions && sessions.length === 0 ? (
        <div className="empty-state">No syllabus sessions added yet.</div>
      ) : (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 90 }}>Session</th>
                <th>Key Topics Covered</th>
                {isTeacher && <th aria-label="Actions" />}
              </tr>
            </thead>
            <tbody>
              {sessions?.map((session) => (
                <tr key={session.id}>
                  <td className="font-mono">{session.session_number}</td>
                  <td>{session.topics}</td>
                  {isTeacher && (
                    <td className="tk-actions">
                      <button type="button" onClick={() => openEdit(session)}>
                        Edit
                      </button>
                      <button type="button" className="tt-danger" onClick={() => handleDelete(session)}>
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isTeacher && (
        <Modal show={editing !== null} onHide={() => setEditing(null)} centered>
          <Form onSubmit={handleSave}>
            <Modal.Header closeButton>
              <Modal.Title className="h5">{editing === "new" ? "Add session" : "Edit session"}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              {formError && <Alert variant="danger">{formError}</Alert>}
              <Form.Group className="mb-3" controlId="syl-number">
                <Form.Label>Session number</Form.Label>
                <Form.Control
                  type="number"
                  min={1}
                  value={form.session_number}
                  onChange={(e) => setForm({ ...form, session_number: Number(e.target.value) })}
                  required
                />
              </Form.Group>
              <Form.Group controlId="syl-topics">
                <Form.Label>Key topics covered</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={form.topics}
                  onChange={(e) => setForm({ ...form, topics: e.target.value })}
                  required
                />
              </Form.Group>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="outline-secondary" onClick={() => setEditing(null)} disabled={saving}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </Button>
            </Modal.Footer>
          </Form>
        </Modal>
      )}
    </AppShell>
  );
}
