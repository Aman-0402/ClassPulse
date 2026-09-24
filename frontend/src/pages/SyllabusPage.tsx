import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Form, Modal } from "react-bootstrap";
import {
  deleteSyllabusSession,
  getAnalytics,
  getAttendanceLookup,
  getSyllabus,
  logout,
  markSyllabusCompletion,
  saveSyllabusSession,
  unmarkSyllabusCompletion,
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

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Shown to both roles — the course TOC/syllabus. A teacher/admin gets
// add/edit/delete for sessions, plus a per-section "mark complete" flow
// (date + present count, auto-fetched from that section's attendance where
// available, always editable). A student sees the same list read-only, with
// only their own section's completion status.
export default function SyllabusPage() {
  const [sessions, setSessions] = useState<SyllabusSession[] | null>(null);
  const [knownSections, setKnownSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState<SyllabusSession | "new" | null>(null);
  const [form, setForm] = useState<SyllabusSessionInput>({ session_number: 1, topics: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [marking, setMarking] = useState<SyllabusSession | null>(null);
  const [markDate, setMarkDate] = useState(todayIso());
  const [markCount, setMarkCount] = useState<number | "">("");
  const [markLookedUp, setMarkLookedUp] = useState(false);
  const [markLoading, setMarkLoading] = useState(false);
  const [markSaving, setMarkSaving] = useState(false);
  const [markError, setMarkError] = useState<string | null>(null);

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

  useEffect(() => {
    if (!isTeacher) return;
    getAnalytics()
      .then((result) => setKnownSections(result.available_sections))
      .catch(() => {});
  }, [isTeacher]);

  const sections = useMemo(() => {
    const all = new Set<string>(knownSections);
    (sessions ?? []).forEach((s) => s.completions.forEach((c) => all.add(c.section)));
    return [...all].sort();
  }, [knownSections, sessions]);

  useEffect(() => {
    if (isTeacher && !section && sections.length > 0) setSection(sections[0]);
  }, [isTeacher, section, sections]);

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

  const completionFor = (session: SyllabusSession) => session.completions.find((c) => c.section === section);

  const openMark = (session: SyllabusSession) => {
    const existing = completionFor(session);
    setMarkDate(existing?.date ?? todayIso());
    setMarkCount(existing?.present_count ?? "");
    setMarkLookedUp(false);
    setMarkError(null);
    setMarking(session);
  };

  // Re-fetches the section's attendance whenever the date changes, so the
  // count is pre-filled where it can be — the admin can still type over it.
  useEffect(() => {
    if (!marking || !section || !markDate) return;
    let active = true;
    setMarkLoading(true);
    getAttendanceLookup(section, markDate)
      .then((count) => {
        if (!active) return;
        if (count !== null) {
          setMarkCount(count);
          setMarkLookedUp(true);
        } else {
          setMarkLookedUp(false);
        }
      })
      .catch(() => {})
      .finally(() => active && setMarkLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [markDate, marking]);

  const handleMarkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!marking) return;
    setMarkError(null);
    if (markCount === "" || markCount < 0) {
      setMarkError("Enter how many students were present.");
      return;
    }
    setMarkSaving(true);
    try {
      await markSyllabusCompletion(marking.id, { section, date: markDate, present_count: Number(markCount) });
      setMarking(null);
      load();
      notifySuccess("Marked Complete", `Session ${marking.session_number} marked complete for Section ${section}.`);
    } catch (err: any) {
      setMarkError(firstError(err?.response?.data));
    } finally {
      setMarkSaving(false);
    }
  };

  const handleUnmark = async (session: SyllabusSession) => {
    const ok = await confirmAction(
      "Unmark this session?",
      `Session ${session.session_number} will show as not completed for Section ${section} again.`,
      "Unmark"
    );
    if (!ok) return;
    try {
      await unmarkSyllabusCompletion(session.id, section);
      load();
    } catch {
      notifyError("Failed", "Could not unmark that session.");
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
        subtitle={
          isTeacher
            ? "Session-wise topics covered. Pick a section to mark sessions complete for it."
            : "Session-wise topics covered in this course."
        }
        actions={isTeacher ? <Button onClick={openNew}>+ Add session</Button> : undefined}
      />

      {error && <Alert variant="danger">{error}</Alert>}

      {isTeacher && sections.length > 0 && (
        <div className="tt-sections" role="tablist" aria-label="Section">
          {sections.map((s) => (
            <button
              key={s}
              type="button"
              role="tab"
              aria-selected={section === s}
              className={`late-chip ${section === s ? "late-chip-on" : ""}`}
              onClick={() => setSection(s)}
            >
              BBA III {s}
            </button>
          ))}
        </div>
      )}

      {sessions && sessions.length === 0 ? (
        <div className="empty-state">No syllabus sessions added yet.</div>
      ) : (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 90 }}>Session</th>
                <th>Key Topics Covered</th>
                <th style={{ width: 220 }}>Status{isTeacher && section ? ` — Section ${section}` : ""}</th>
                {isTeacher && <th aria-label="Actions" style={{ width: 160 }} />}
              </tr>
            </thead>
            <tbody>
              {sessions?.map((session) => {
                const own = isTeacher ? completionFor(session) : session.completions[0];
                return (
                  <tr key={session.id}>
                    <td className="font-mono">{session.session_number}</td>
                    <td>{session.topics}</td>
                    <td>
                      {own ? (
                        <span className="stamp stamp-present">
                          Completed — {own.date}
                          {own.present_count !== undefined ? ` · ${own.present_count} present` : ""}
                        </span>
                      ) : (
                        <span className="stamp stamp-neutral">Pending</span>
                      )}
                    </td>
                    {isTeacher && (
                      <td className="tk-actions">
                        {!section ? (
                          <span className="text-muted small">Pick a section</span>
                        ) : own ? (
                          <>
                            <button type="button" onClick={() => openMark(session)}>
                              Edit
                            </button>
                            <button type="button" className="tt-danger" onClick={() => handleUnmark(session)}>
                              Unmark
                            </button>
                          </>
                        ) : (
                          <button type="button" onClick={() => openMark(session)}>
                            Mark complete
                          </button>
                        )}
                        <button type="button" onClick={() => openEdit(session)}>
                          Edit topic
                        </button>
                        <button type="button" className="tt-danger" onClick={() => handleDelete(session)}>
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
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

      {isTeacher && (
        <Modal show={marking !== null} onHide={() => setMarking(null)} centered>
          <Form onSubmit={handleMarkSubmit}>
            <Modal.Header closeButton>
              <Modal.Title className="h5">
                Mark Session {marking?.session_number} complete — Section {section}
              </Modal.Title>
            </Modal.Header>
            <Modal.Body>
              {markError && <Alert variant="danger">{markError}</Alert>}
              <Form.Group className="mb-3" controlId="mark-date">
                <Form.Label>Date the class was held</Form.Label>
                <Form.Control type="date" value={markDate} onChange={(e) => setMarkDate(e.target.value)} required />
              </Form.Group>
              <Form.Group controlId="mark-count">
                <Form.Label>Students present</Form.Label>
                <Form.Control
                  type="number"
                  min={0}
                  value={markCount}
                  onChange={(e) => setMarkCount(e.target.value === "" ? "" : Number(e.target.value))}
                  required
                />
                <Form.Text className="text-muted">
                  {markLoading
                    ? "Checking attendance records for that date..."
                    : markLookedUp
                    ? "Fetched from that day's attendance — edit if it's wrong."
                    : "No attendance record found for that date/section — enter it manually."}
                </Form.Text>
              </Form.Group>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="outline-secondary" onClick={() => setMarking(null)} disabled={markSaving}>
                Cancel
              </Button>
              <Button type="submit" disabled={markSaving}>
                {markSaving ? "Saving..." : "Mark Complete"}
              </Button>
            </Modal.Footer>
          </Form>
        </Modal>
      )}
    </AppShell>
  );
}
