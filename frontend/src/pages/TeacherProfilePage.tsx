import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Form, Button } from "react-bootstrap";
import { getTeacherProfile, getTodaySchedule, updateTeacherEmail, logout } from "../api/client";
import type { ScheduleSlot } from "../api/client";
import AppShell from "../components/AppShell";
import LoadingScreen from "../components/LoadingScreen";
import { formatTime } from "../utils/time";
import { TRAINING_SUBJECT } from "../constants";

interface TeacherProfile {
  full_name: string;
  email: string;
  username: string;
  pending_edit_requests_count: number;
}

export default function TeacherProfilePage() {
  const [profile, setProfile] = useState<TeacherProfile | null>(null);
  const [scheduleDay, setScheduleDay] = useState<string | null>(null);
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
  const [editingEmail, setEditingEmail] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailSaving, setEmailSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getTeacherProfile()
      .then(setProfile)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
    getTodaySchedule()
      .then((data) => {
        setScheduleDay(data.day);
        setSlots(data.slots);
      })
      .catch(() => {
        // Timetable card is a convenience — the rest of the dashboard still works without it.
      });
  }, [navigate]);

  const handleStartEditEmail = () => {
    setEmailInput(profile?.email ?? "");
    setEmailError(null);
    setEditingEmail(true);
  };

  const handleSaveEmail = async () => {
    setEmailError(null);
    setEmailSaving(true);
    try {
      const updated = await updateTeacherEmail(emailInput);
      setProfile((prev) => (prev ? { ...prev, email: updated.email } : prev));
      setEditingEmail(false);
    } catch (err: any) {
      setEmailError(err?.response?.data?.email?.[0] || "Enter a valid email address.");
    } finally {
      setEmailSaving(false);
    }
  };

  if (!profile) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  const displayName = profile.full_name || profile.username;
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const pending = profile.pending_edit_requests_count;
  const initials = displayName
    .split(/\s+/)
    .map((part) => part.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const actions = [
    { to: "/teacher/start-attendance", icon: "▶", title: "Start Attendance", hint: "Open a live QR session", primary: true, badge: 0 },
    {
      to: "/teacher/corrections",
      icon: "✎",
      title: "Corrections",
      hint: pending ? `${pending} awaiting review` : "No pending requests",
      primary: false,
      badge: pending,
    },
    { to: "/teacher/timetable", icon: "▥", title: "Timetable", hint: "Edit every section's classes", primary: false, badge: 0 },
    { to: "/teacher/tasks", icon: "☑", title: "Tasks", hint: "Post tasks to a section", primary: false, badge: 0 },
    { to: "/teacher/question-bank", icon: "❓", title: "Question Bank", hint: "MCQ and practical questions", primary: false, badge: 0 },
    { to: "/teacher/exams", icon: "📝", title: "Exams", hint: "Schedule exams per section", primary: false, badge: 0 },
    { to: "/teacher/students", icon: "☰", title: "Student Data", hint: "Profiles and contact details", primary: false, badge: 0 },
    { to: "/teacher/analytics", icon: "▤", title: "Analytics", hint: "Attendance percentages", primary: false, badge: 0 },
    { to: "/teacher/day-attendance", icon: "▦", title: "Day-wise", hint: "Who was present, by day", primary: false, badge: 0 },
  ];

  return (
    <AppShell>
      <section className="tp-hero">
        <div className="tp-avatar" aria-hidden="true">
          {initials || "T"}
        </div>
        <div className="tp-hero-text">
          <div className="tp-hello">{greeting}</div>
          <h1 className="tp-name">{displayName}</h1>
          <div className="tp-chips">
            <span className="tp-chip">Teacher</span>
            <span className="tp-chip tp-chip-soft">{TRAINING_SUBJECT}</span>
          </div>
        </div>
        <Link to="/teacher/start-attendance" className="tp-hero-cta">
          Start Attendance
        </Link>
      </section>

      <section className="tp-actions" aria-label="Quick actions">
        {actions.map((action) => (
          <Link key={action.to} to={action.to} className={`tp-action ${action.primary ? "tp-action-primary" : ""}`}>
            <span className="tp-action-icon" aria-hidden="true">
              {action.icon}
            </span>
            <span className="tp-action-body">
              <span className="tp-action-title">{action.title}</span>
              <span className="tp-action-hint">{action.hint}</span>
            </span>
            {action.badge > 0 && <span className="tp-action-badge">{action.badge}</span>}
          </Link>
        ))}
      </section>

      <div className="tp-grid">
        <Card>
          <Card.Body>
            <h2 className="tp-card-title">Account</h2>
            <dl className="tp-details">
              <div>
                <dt>Name</dt>
                <dd>{displayName}</dd>
              </div>
              <div>
                <dt>Username</dt>
                <dd className="font-mono">{profile.username}</dd>
              </div>
              <div>
                <dt>Subject</dt>
                <dd>{TRAINING_SUBJECT}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>
                  {editingEmail ? (
                    <div>
                      <Form.Control
                        size="sm"
                        type="email"
                        value={emailInput}
                        onChange={(e) => setEmailInput(e.target.value)}
                        autoFocus
                      />
                      {emailError && <div className="text-danger small mt-1">{emailError}</div>}
                      <div className="d-flex gap-2 mt-2">
                        <Button size="sm" onClick={handleSaveEmail} disabled={emailSaving}>
                          {emailSaving ? "Saving..." : "Save"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline-secondary"
                          onClick={() => setEditingEmail(false)}
                          disabled={emailSaving}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="d-flex align-items-center gap-2 flex-wrap">
                      <span className="text-break">{profile.email || "Not added yet"}</span>
                      <Button size="sm" variant="outline-secondary" onClick={handleStartEditEmail}>
                        Edit
                      </Button>
                    </div>
                  )}
                </dd>
              </div>
            </dl>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body>
            <div className="d-flex justify-content-between align-items-baseline flex-wrap gap-2 mb-3">
              <h2 className="tp-card-title mb-0">{scheduleDay ? `${scheduleDay}'s Timetable` : "Today's Timetable"}</h2>
              <span className="text-muted small">
                {slots.length} session{slots.length === 1 ? "" : "s"}
              </span>
            </div>
            {slots.length === 0 ? (
              <p className="text-muted mb-0">No training sessions scheduled today.</p>
            ) : (
              <ol className="tp-timeline">
                {slots.map((slot, index) => {
                  const live = slot.session_status === "active";
                  return (
                    <li key={index} className={`tp-slot ${live ? "tp-slot-live" : ""}`}>
                      <button
                        type="button"
                        className="tp-slot-btn"
                        onClick={() =>
                          slot.session_id
                            ? navigate(`/teacher/session/${slot.session_id}`)
                            : navigate("/teacher/start-attendance", {
                                state: { subject: slot.subject, section: slot.section, periods: slot.periods },
                              })
                        }
                      >
                        <span className="tp-slot-time font-mono">
                          {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                        </span>
                        <span className="tp-slot-main">
                          <span>{slot.subject}</span>
                          <span className="stamp stamp-neutral">BBA III {slot.section}</span>
                        </span>
                        <span className={`action-pill ${live ? "action-pill-live" : ""}`}>
                          {live ? "View Live" : slot.session_id ? "View Attendance" : "Start"}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>
            )}
          </Card.Body>
        </Card>
      </div>
    </AppShell>
  );
}
