import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button, Form, Modal } from "react-bootstrap";
import {
  deleteExam,
  getAnalytics,
  getExams,
  getPracticalQuestions,
  logout,
  saveExam,
  setExamManualStatus,
} from "../../api/client";
import type { Exam, ExamInput, PracticalQuestion } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { confirmAction, notifyError, notifySuccess } from "../../utils/alerts";
import { formatDateTime } from "../../utils/time";

// datetime-local wants "YYYY-MM-DDTHH:MM" in LOCAL time, but Date.toISOString()
// is UTC - build the local string by hand instead of slicing the ISO string.
function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function defaultWindow(): { start: string; end: string } {
  const start = new Date();
  start.setMinutes(start.getMinutes() + 5, 0, 0);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return { start: toLocalInputValue(start.toISOString()), end: toLocalInputValue(end.toISOString()) };
}

function emptyForm(section: string): ExamInput {
  const { start, end } = defaultWindow();
  return {
    title: "Exam",
    section,
    easy_practical: 0,
    hard_practical: 0,
    start_time: start,
    end_time: end,
    manual_status: "auto",
  };
}

function firstError(data: any): string {
  if (!data) return "Could not save this exam.";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data)) return String(data[0]);
  const first = Object.values(data)[0];
  return Array.isArray(first) ? String(first[0]) : String(first ?? "Could not save this exam.");
}

const STATUS_LABEL: Record<Exam["manual_status"], string> = {
  auto: "Follows schedule",
  forced_open: "Forced open",
  forced_closed: "Forced closed",
};

export default function ExamsPage() {
  const [exams, setExams] = useState<Exam[] | null>(null);
  const [practicals, setPracticals] = useState<PracticalQuestion[] | null>(null);
  const [knownSections, setKnownSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Exam | "new" | null>(null);
  const [form, setForm] = useState<ExamInput>(emptyForm(""));
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => {
    Promise.all([getExams(), getPracticalQuestions()])
      .then(([examResult, practicalResult]) => {
        setExams(examResult);
        setPracticals(practicalResult);
        setError(null);
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load exams.");
        }
      });
  }, [navigate]);

  useEffect(() => {
    load();
    getAnalytics()
      .then((result) => setKnownSections(result.available_sections))
      .catch(() => {});
  }, [load]);

  const sections = useMemo(() => {
    const all = new Set<string>(knownSections);
    (exams ?? []).forEach((e) => all.add(e.section));
    return [...all].sort();
  }, [knownSections, exams]);

  useEffect(() => {
    if (!section && sections.length > 0) setSection(sections[0]);
  }, [section, sections]);

  const shown = useMemo(() => (exams ?? []).filter((e) => e.section === section), [exams, section]);
  const easyOptions = (practicals ?? []).filter((p) => p.difficulty === "easy" && p.is_active);
  const hardOptions = (practicals ?? []).filter((p) => p.difficulty === "hard" && p.is_active);

  const openNew = () => {
    const form = emptyForm(section);
    form.easy_practical = easyOptions[0]?.id ?? 0;
    form.hard_practical = hardOptions[0]?.id ?? 0;
    setForm(form);
    setFormError(null);
    setEditing("new");
  };

  const openEdit = (exam: Exam) => {
    setForm({
      title: exam.title,
      section: exam.section,
      easy_practical: exam.easy_practical,
      hard_practical: exam.hard_practical,
      start_time: toLocalInputValue(exam.start_time),
      end_time: toLocalInputValue(exam.end_time),
      manual_status: exam.manual_status,
    });
    setFormError(null);
    setEditing(exam);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!form.easy_practical || !form.hard_practical) {
      setFormError("Add at least one active easy and one active hard practical question in the Question Bank first.");
      return;
    }
    setSaving(true);
    try {
      const payload: ExamInput = {
        ...form,
        start_time: new Date(form.start_time).toISOString(),
        end_time: new Date(form.end_time).toISOString(),
      };
      const saved = await saveExam(payload, editing !== "new" && editing ? editing.id : undefined);
      setEditing(null);
      setSection(saved.section);
      load();
      notifySuccess("Exam Saved", "The exam has been scheduled.");
    } catch (err: any) {
      setFormError(firstError(err?.response?.data));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleStatus = async (exam: Exam, status: Exam["manual_status"]) => {
    try {
      await setExamManualStatus(exam.id, status);
      load();
    } catch {
      notifyError("Update Failed", "Could not change this exam's status.");
    }
  };

  const handleDelete = async (exam: Exam) => {
    const ok = await confirmAction("Delete this exam?", exam.title, "Delete");
    if (!ok) return;
    try {
      await deleteExam(exam.id);
      load();
    } catch {
      notifyError("Delete Failed", "Could not delete that exam. It may already have student attempts.");
    }
  };

  if (!exams && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin"
        title="Exams"
        subtitle="Schedule an exam window per section. Each student gets 5 random MCQs plus your chosen easy + hard practical."
        actions={<Button onClick={openNew}>+ Schedule exam</Button>}
      />

      {error && <Alert variant="danger">{error}</Alert>}

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

      {shown.length === 0 ? (
        <div className="empty-state">No exams scheduled for this section yet.</div>
      ) : (
        <div className="tk-list">
          {shown.map((exam) => (
            <div key={exam.id} className="tk-card">
              <div className="tk-card-head">
                <h3 className="tk-title">{exam.title}</h3>
                <span className={`stamp ${exam.is_open ? "stamp-present" : "stamp-absent"}`}>
                  {exam.is_open ? "Open now" : "Closed"}
                </span>
              </div>
              <p className="tk-desc">
                {formatDateTime(exam.start_time)} → {formatDateTime(exam.end_time)}
                <br />
                Easy: {exam.easy_practical_text} · Hard: {exam.hard_practical_text}
              </p>
              <div className="tk-meta">
                <span>{STATUS_LABEL[exam.manual_status]}</span>
                <div className="tk-actions">
                  <Link to={`/teacher/exams/${exam.id}/results`}>Results</Link>
                  <button type="button" onClick={() => openEdit(exam)}>
                    Edit
                  </button>
                  {exam.manual_status !== "forced_open" && (
                    <button type="button" onClick={() => handleToggleStatus(exam, "forced_open")}>
                      Force open
                    </button>
                  )}
                  {exam.manual_status !== "forced_closed" && (
                    <button type="button" onClick={() => handleToggleStatus(exam, "forced_closed")}>
                      Force close
                    </button>
                  )}
                  {exam.manual_status !== "auto" && (
                    <button type="button" onClick={() => handleToggleStatus(exam, "auto")}>
                      Follow schedule
                    </button>
                  )}
                  <button type="button" className="tt-danger" onClick={() => handleDelete(exam)}>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal show={editing !== null} onHide={() => setEditing(null)} centered size="lg">
        <Form onSubmit={handleSave}>
          <Modal.Header closeButton>
            <Modal.Title className="h5">{editing === "new" ? "Schedule exam" : "Edit exam"}</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {formError && <Alert variant="danger">{formError}</Alert>}
            <div className="d-flex gap-3">
              <Form.Group className="mb-3 flex-fill" controlId="exam-title">
                <Form.Label>Title</Form.Label>
                <Form.Control
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  maxLength={200}
                  required
                />
              </Form.Group>
              <Form.Group className="mb-3" style={{ minWidth: 120 }} controlId="exam-section">
                <Form.Label>Section</Form.Label>
                <Form.Control
                  value={form.section}
                  onChange={(e) => setForm({ ...form, section: e.target.value })}
                  maxLength={10}
                  required
                />
              </Form.Group>
            </div>
            <div className="d-flex gap-3">
              <Form.Group className="mb-3 flex-fill" controlId="exam-easy">
                <Form.Label>Easy practical</Form.Label>
                <Form.Select
                  value={form.easy_practical || ""}
                  onChange={(e) => setForm({ ...form, easy_practical: Number(e.target.value) })}
                  required
                >
                  <option value="" disabled>
                    Select...
                  </option>
                  {easyOptions.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.text.slice(0, 60)}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
              <Form.Group className="mb-3 flex-fill" controlId="exam-hard">
                <Form.Label>Hard practical</Form.Label>
                <Form.Select
                  value={form.hard_practical || ""}
                  onChange={(e) => setForm({ ...form, hard_practical: Number(e.target.value) })}
                  required
                >
                  <option value="" disabled>
                    Select...
                  </option>
                  {hardOptions.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.text.slice(0, 60)}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </div>
            <div className="d-flex gap-3">
              <Form.Group className="mb-3 flex-fill" controlId="exam-start">
                <Form.Label>Opens</Form.Label>
                <Form.Control
                  type="datetime-local"
                  value={form.start_time}
                  onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                  required
                />
              </Form.Group>
              <Form.Group className="mb-3 flex-fill" controlId="exam-end">
                <Form.Label>Closes</Form.Label>
                <Form.Control
                  type="datetime-local"
                  value={form.end_time}
                  onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                  required
                />
              </Form.Group>
            </div>
            <Form.Group controlId="exam-manual">
              <Form.Label>Manual override</Form.Label>
              <Form.Select
                value={form.manual_status}
                onChange={(e) => setForm({ ...form, manual_status: e.target.value as Exam["manual_status"] })}
              >
                <option value="auto">Follow the schedule above</option>
                <option value="forced_open">Force open now, ignore schedule</option>
                <option value="forced_closed">Force closed now, ignore schedule</option>
              </Form.Select>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="outline-secondary" onClick={() => setEditing(null)} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save exam"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </AppShell>
  );
}
