import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Spinner, Table, Form, Button } from "react-bootstrap";
import { getTeacherProfile, getTodaySchedule, updateTeacherEmail, logout } from "../api/client";
import type { ScheduleSlot } from "../api/client";
import AppShell from "../components/AppShell";
import { formatTime } from "../utils/time";
import { TRAINING_SUBJECT } from "../constants";

interface TeacherProfile {
  full_name: string;
  email: string;
  username: string;
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
        <Spinner animation="border" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="h3 mb-4">Welcome, {profile.full_name || profile.username}</h1>
      <Card style={{ maxWidth: 480 }}>
        <Card.Body>
          <span className="stamp stamp-neutral mb-3 d-inline-block">Teacher</span>
          <dl className="row mb-0">
            <dt className="col-4 text-muted fw-normal">Name</dt>
            <dd className="col-8">{profile.full_name || profile.username}</dd>
            <dt className="col-4 text-muted fw-normal">Subject</dt>
            <dd className="col-8">{TRAINING_SUBJECT}</dd>
            <dt className="col-4 text-muted fw-normal">Email</dt>
            <dd className="col-8">
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
            </dd>
          </dl>
        </Card.Body>
      </Card>
      <Link to="/teacher/start-attendance" className="btn btn-primary mt-3">
        Start Attendance
      </Link>

      {scheduleDay && (
        <Card className="mt-4" style={{ maxWidth: 820 }}>
          <Card.Body>
            <h2 className="h6 mb-3">{scheduleDay}'s Timetable</h2>
            {slots.length === 0 ? (
              <p className="text-muted mb-0">No training sessions scheduled today.</p>
            ) : (
              <div className="table-responsive">
                <Table size="sm" borderless hover className="mb-0">
                  <tbody>
                    {slots.map((slot, index) => (
                      <tr
                        key={index}
                        role="button"
                        style={{ cursor: "pointer" }}
                        onClick={() =>
                          slot.session_id
                            ? navigate(`/teacher/session/${slot.session_id}`)
                            : navigate("/teacher/start-attendance", {
                                state: { subject: slot.subject, section: slot.section, periods: slot.periods },
                              })
                        }
                      >
                        <td className="text-muted font-mono text-nowrap">
                          {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                        </td>
                        <td className="text-nowrap">{slot.subject}</td>
                        <td className="text-nowrap">
                          <span className="stamp stamp-neutral">BBA III {slot.section}</span>
                        </td>
                        <td className="text-end text-nowrap">
                          {slot.session_id ? (
                            <span className={`stamp ${slot.session_status === "active" ? "stamp-present" : "stamp-neutral"}`}>
                              {slot.session_status === "active" ? "View live" : "View attendance"}
                            </span>
                          ) : (
                            <span className="stamp stamp-neutral">Start attendance</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </Card.Body>
        </Card>
      )}
    </AppShell>
  );
}
