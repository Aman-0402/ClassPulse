import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Spinner, Table } from "react-bootstrap";
import { getTeacherProfile, getTodaySchedule, logout } from "../api/client";
import type { ScheduleSlot } from "../api/client";
import AppShell from "../components/AppShell";
import { formatTime } from "../utils/time";

interface TeacherProfile {
  full_name: string;
  email: string;
  username: string;
}

export default function TeacherProfilePage() {
  const [profile, setProfile] = useState<TeacherProfile | null>(null);
  const [scheduleDay, setScheduleDay] = useState<string | null>(null);
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
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
            <dt className="col-4 text-muted fw-normal">Email</dt>
            <dd className="col-8 text-break">{profile.email}</dd>
          </dl>
        </Card.Body>
      </Card>
      <Link to="/teacher/start-attendance" className="btn btn-primary mt-3">
        Start Attendance
      </Link>

      {scheduleDay && (
        <Card className="mt-4" style={{ maxWidth: 480 }}>
          <Card.Body>
            <h2 className="h6 mb-3">{scheduleDay}'s Timetable</h2>
            {slots.length === 0 ? (
              <p className="text-muted mb-0">No training sessions scheduled today.</p>
            ) : (
              <Table size="sm" borderless className="mb-0">
                <tbody>
                  {slots.map((slot, index) => (
                    <tr key={index}>
                      <td className="text-muted font-mono">
                        {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                      </td>
                      <td>{slot.subject}</td>
                      <td>
                        <span className="stamp stamp-neutral">BBA III {slot.section}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card.Body>
        </Card>
      )}
    </AppShell>
  );
}
