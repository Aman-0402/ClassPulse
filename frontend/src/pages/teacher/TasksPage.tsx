import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Form, Modal } from "react-bootstrap";
import { deleteTask, getAnalytics, getTeacherTasks, logout, saveTask } from "../../api/client";
import type { Task, TaskInput } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { confirmAction, notifyError, notifySuccess } from "../../utils/alerts";
import { formatDateTime } from "../../utils/time";

const EMPTY: TaskInput = { title: "", description: "", section: "", due_date: null };

function firstError(data: any): string {
  if (!data) return "Could not save this task.";
  if (typeof data.detail === "string") return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? String(first[0]) : String(first ?? "Could not save this task.");
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [knownSections, setKnownSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Task | "new" | null>(null);
  const [form, setForm] = useState<TaskInput>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => {
    getTeacherTasks()
      .then((result) => {
        setTasks(result);
        setError(null);
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load tasks.");
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
    (tasks ?? []).forEach((t) => all.add(t.section));
    return [...all].sort();
  }, [knownSections, tasks]);

  useEffect(() => {
    if (!section && sections.length > 0) setSection(sections[0]);
  }, [section, sections]);

  const shown = useMemo(() => (tasks ?? []).filter((t) => t.section === section), [tasks, section]);

  const openNew = () => {
    setForm({ ...EMPTY, section });
    setFormError(null);
    setEditing("new");
  };

  const openEdit = (task: Task) => {
    setForm({ title: task.title, description: task.description, section: task.section, due_date: task.due_date });
    setFormError(null);
    setEditing(task);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      const saved = await saveTask(form, editing !== "new" && editing ? editing.id : undefined);
      setEditing(null);
      setSection(saved.section);
      load();
      notifySuccess("Task Saved", "The task has been posted to the section.");
    } catch (err: any) {
      setFormError(firstError(err?.response?.data));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (task: Task) => {
    const ok = await confirmAction("Delete this task?", task.title, "Delete");
    if (!ok) return;
    try {
      await deleteTask(task.id);
      load();
    } catch {
      notifyError("Delete Failed", "Could not delete that task.");
    }
  };

  if (!tasks && !error) {
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
        title="Tasks"
        subtitle="Post a task or assignment to a section. Students see it, read-only, on their own portal."
        actions={<Button onClick={openNew}>+ Add task</Button>}
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
        <button
          type="button"
          className="late-chip"
          onClick={() => {
            setSection("");
            openNew();
          }}
        >
          + New section
        </button>
      </div>

      {shown.length === 0 ? (
        <div className="empty-state">No tasks posted for this section yet.</div>
      ) : (
        <div className="tk-list">
          {shown.map((task) => (
            <div key={task.id} className="tk-card">
              <div className="tk-card-head">
                <h3 className="tk-title">{task.title}</h3>
                {task.due_date && <span className="stamp stamp-neutral">Due {task.due_date}</span>}
              </div>
              {task.description && <p className="tk-desc">{task.description}</p>}
              <div className="tk-meta">
                <span>Posted by {task.created_by_name || "—"} · {formatDateTime(task.created_at)}</span>
                <div className="tk-actions">
                  <button type="button" onClick={() => openEdit(task)}>
                    Edit
                  </button>
                  <button type="button" className="tt-danger" onClick={() => handleDelete(task)}>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal show={editing !== null} onHide={() => setEditing(null)} centered>
        <Form onSubmit={handleSave}>
          <Modal.Header closeButton>
            <Modal.Title className="h5">{editing === "new" ? "Add task" : "Edit task"}</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {formError && <Alert variant="danger">{formError}</Alert>}
            <Form.Group className="mb-3" controlId="tk-section">
              <Form.Label>Section</Form.Label>
              <Form.Control
                value={form.section}
                onChange={(e) => setForm({ ...form, section: e.target.value })}
                list="tk-section-list"
                placeholder="e.g. A"
                maxLength={10}
                required
              />
              <datalist id="tk-section-list">
                {sections.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>
            </Form.Group>
            <Form.Group className="mb-3" controlId="tk-title">
              <Form.Label>Title</Form.Label>
              <Form.Control
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                maxLength={200}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3" controlId="tk-description">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea"
                rows={4}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </Form.Group>
            <Form.Group controlId="tk-due">
              <Form.Label>Due date (optional)</Form.Label>
              <Form.Control
                type="date"
                value={form.due_date ?? ""}
                onChange={(e) => setForm({ ...form, due_date: e.target.value || null })}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="outline-secondary" onClick={() => setEditing(null)} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save task"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </AppShell>
  );
}
