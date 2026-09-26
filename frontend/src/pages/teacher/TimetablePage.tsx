import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Form, Modal } from "react-bootstrap";
import { deleteTimetableSlot, getAnalytics, getTimetable, logout, saveTimetableSlot } from "../../api/client";
import type { TimetableSlot, TimetableSlotInput } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { confirmAction, notifyError, notifySuccess } from "../../utils/alerts";
import { formatTime } from "../../utils/time";
import { TRAINING_SUBJECT } from "../../constants";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const EMPTY: TimetableSlotInput = {
  day_of_week: 0,
  start_time: "09:00",
  end_time: "09:50",
  section: "",
  subject: TRAINING_SUBJECT,
};

// The API returns "HH:MM:SS"; <input type="time"> wants "HH:MM".
const hhmm = (value: string) => value.slice(0, 5);

function firstError(data: any): string {
  if (!data) return "Could not save this slot.";
  if (typeof data.detail === "string") return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? String(first[0]) : String(first ?? "Could not save this slot.");
}

export default function TimetablePage() {
  const [slots, setSlots] = useState<TimetableSlot[] | null>(null);
  const [knownSections, setKnownSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<TimetableSlot | "new" | null>(null);
  const [form, setForm] = useState<TimetableSlotInput>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => {
    getTimetable()
      .then((result) => {
        setSlots(result);
        setError(null);
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load the timetable.");
        }
      });
  }, [navigate]);

  useEffect(() => {
    load();
    // Sections that have students, so a brand-new section can still be picked.
    getAnalytics()
      .then((result) => setKnownSections(result.available_sections))
      .catch(() => {});
  }, [load]);

  const sections = useMemo(() => {
    const all = new Set<string>(knownSections);
    (slots ?? []).forEach((slot) => all.add(slot.section));
    return [...all].sort();
  }, [knownSections, slots]);

  useEffect(() => {
    if (!section && sections.length > 0) setSection(sections[0]);
  }, [section, sections]);

  const shown = useMemo(
    () => (slots ?? []).filter((slot) => slot.section === section),
    [slots, section]
  );

  const openNew = (day = 0, forSection = section) => {
    setForm({ ...EMPTY, day_of_week: day, section: forSection });
    setFormError(null);
    setEditing("new");
  };

  const openEdit = (slot: TimetableSlot) => {
    setForm({
      day_of_week: slot.day_of_week,
      start_time: hhmm(slot.start_time),
      end_time: hhmm(slot.end_time),
      section: slot.section,
      subject: slot.subject,
    });
    setFormError(null);
    setEditing(slot);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      const saved = await saveTimetableSlot(form, editing !== "new" && editing ? editing.id : undefined);
      setEditing(null);
      setSection(saved.section);
      load();
      notifySuccess("Timetable Updated", "The slot has been saved.");
    } catch (err: any) {
      setFormError(firstError(err?.response?.data));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (slot: TimetableSlot) => {
    const ok = await confirmAction(
      "Delete this slot?",
      `${slot.day_name} ${formatTime(slot.start_time)} - ${formatTime(slot.end_time)} · ${slot.subject} (Section ${slot.section})`,
      "Delete"
    );
    if (!ok) return;
    try {
      await deleteTimetableSlot(slot.id);
      load();
    } catch {
      notifyError("Delete Failed", "Could not delete that slot.");
    }
  };

  if (!slots && !error) {
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
        title="Timetable"
        subtitle="Set each section's weekly classes. Teachers see these on their dashboard and Start Attendance pre-fills from them."
        actions={
          <Button onClick={() => openNew()}>
            + Add slot
          </Button>
        }
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
        <button type="button" className="late-chip" onClick={() => openNew(0, "")}>
          + New section
        </button>
      </div>

      <div className="tt-grid">
        {DAYS.map((day, index) => {
          const daySlots = shown.filter((slot) => slot.day_of_week === index);
          return (
            <section key={day} className="tt-day">
              <div className="tt-day-head">
                <strong>{day}</strong>
                <button type="button" className="tt-add" onClick={() => openNew(index)} aria-label={`Add slot on ${day}`}>
                  +
                </button>
              </div>
              {daySlots.length === 0 ? (
                <div className="tt-empty">No classes</div>
              ) : (
                daySlots.map((slot) => (
                  <div key={slot.id} className="tt-slot">
                    <div className="tt-slot-time font-mono">
                      {formatTime(slot.start_time)} - {formatTime(slot.end_time)}
                    </div>
                    <div className="tt-slot-subject">{slot.subject}</div>
                    <div className="tt-slot-actions">
                      <button type="button" onClick={() => openEdit(slot)}>
                        Edit
                      </button>
                      <button type="button" className="tt-danger" onClick={() => handleDelete(slot)}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </section>
          );
        })}
      </div>

      <Modal show={editing !== null} onHide={() => setEditing(null)} centered>
        <Form onSubmit={handleSave}>
          <Modal.Header closeButton>
            <Modal.Title className="h5">{editing === "new" ? "Add slot" : "Edit slot"}</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {formError && <Alert variant="danger">{formError}</Alert>}
            <Form.Group className="mb-3" controlId="tt-section">
              <Form.Label>Section</Form.Label>
              <Form.Control
                value={form.section}
                onChange={(e) => setForm({ ...form, section: e.target.value })}
                list="tt-section-list"
                placeholder="e.g. A"
                maxLength={10}
                required
              />
              <datalist id="tt-section-list">
                {sections.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>
            </Form.Group>
            <Form.Group className="mb-3" controlId="tt-day">
              <Form.Label>Day</Form.Label>
              <Form.Select
                value={form.day_of_week}
                onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })}
              >
                {DAYS.map((day, index) => (
                  <option key={day} value={index}>
                    {day}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <div className="d-flex gap-3">
              <Form.Group className="mb-3 flex-fill" controlId="tt-start">
                <Form.Label>Starts</Form.Label>
                <Form.Control
                  type="time"
                  value={form.start_time}
                  onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                  required
                />
              </Form.Group>
              <Form.Group className="mb-3 flex-fill" controlId="tt-end">
                <Form.Label>Ends</Form.Label>
                <Form.Control
                  type="time"
                  value={form.end_time}
                  onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                  required
                />
              </Form.Group>
            </div>
            <Form.Group controlId="tt-subject">
              <Form.Label>Subject</Form.Label>
              <Form.Control
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                maxLength={100}
                required
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="outline-secondary" onClick={() => setEditing(null)} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save slot"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </AppShell>
  );
}
