import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Form, Button } from "react-bootstrap";
import { getTeacherProfile, getTodaySchedule, updateTeacherEmail, logout, ADMIN_URL } from "../api/client";
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

  return (
    <AppShell>
      <h1 className="h3 mb-4">Welcome, {profile.full_name || profile.username}</h1>
      {profile.pending_edit_requests_count > 0 && (
        <a
          href={ADMIN_URL}
          target="_blank"
          rel="noreferrer"
          className="d-inline-flex align-items-center gap-2 mb-3 text-decoration-none"
        >
          <span className="action-pill">
            {profile.pending_edit_requests_count} pending profile correction
            {profile.pending_edit_requests_count === 1 ? "" : "s"}
          </span>
          <span className="text-muted small">Review in Admin →</span>
        </a>
      )}
      <Card style={{ maxWidth: 480 }}>
        <Card.Body>
          <span className="stamp stamp-neutral mb-3 d-inline-block">Teacher</span>
          <div className="d-flex flex-column gap-3">
            <div className="info-row">
              <div className="info-row-label">Name</div>
              <div>{profile.full_name || profile.username}</div>
            </div>
            <div className="info-row">
              <div className="info-row-label">Subject</div>
              <div>{TRAINING_SUBJECT}</div>
            </div>
            <div className="info-row">
              <div className="info-row-label">Email</div>
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
                  <span className="text-break">{profile.email}</span>
                  <Button size="sm" variant="outline-secondary" onClick={handleStartEditEmail}>
                    Edit
                  </Button>
                </div>
              )}
            </div>
          </div>
        </Card.Body>
      </Card>
      <Link to="/teacher/start-attendance" className="cta-button mt-3">
        Start Attendance
      </Link>

      {scheduleDay && (
        <Card className="mt-4" style={{ maxWidth: 820 }}>
          <Card.Body>
            <h2 className="h6 mb-3">{scheduleDay}'s Timetable</h2>
            {slots.length === 0 ? (
              <p className="text-muted mb-0">No training sessions scheduled today.</p>
            ) : (
              <div className="d-flex flex-column gap-2">
                {slots.map((slot, index) => (
                  <div
                    key={index}
                    role="button"
                    className="d-flex justify-content-between align-items-center flex-wrap gap-2 timetable-slot"
                    onClick={() =>
                      slot.session_id
                        ? navigate(`/teacher/session/${slot.session_id}`)
                        : navigate("/teacher/start-attendance", {
                            state: { subject: slot.subject, section: slot.section, periods: slot.periods },
                          })
                    }
                  >
                    <div className="d-flex flex-column gap-1">
                      <span className="text-muted font-mono text-nowrap small">
                        {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                      </span>
                      <div className="d-flex align-items-center flex-wrap gap-2">
                        <span>{slot.subject}</span>
                        <span className="stamp stamp-neutral">BBA III {slot.section}</span>
                      </div>
                    </div>
                    {slot.session_id ? (
                      <span className={`action-pill ${slot.session_status === "active" ? "action-pill-live" : ""}`}>
                        {slot.session_status === "active" ? "View Live" : "View Attendance"}
                      </span>
                    ) : (
                      <span className="action-pill">Start Attendance</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card.Body>
        </Card>
      )}
    </AppShell>
  );
}
