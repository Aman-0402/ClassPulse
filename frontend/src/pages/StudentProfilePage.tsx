import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Spinner, Table } from "react-bootstrap";
import { getStudentProfile, getTodaySchedule, logout } from "../api/client";
import type { ScheduleSlot } from "../api/client";
import AppShell from "../components/AppShell";
import { formatTime } from "../utils/time";

interface Profile {
  full_name: string;
  crn: string;
  course: string;
  semester: number;
  section: string;
  email: string;
}

export default function StudentProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [scheduleDay, setScheduleDay] = useState<string | null>(null);
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    getStudentProfile()
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
      <h1 className="h3 mb-4">Welcome, {profile.full_name}</h1>
      <Card style={{ maxWidth: 480 }}>
        <Card.Body>
          <div className="d-flex justify-content-between align-items-start mb-3">
            <span className="stamp stamp-neutral">Student ID</span>
            <span className="font-mono text-muted">{profile.crn}</span>
          </div>
          <dl className="row mb-0">
            <dt className="col-5 text-muted fw-normal">Course</dt>
            <dd className="col-7">{profile.course}</dd>
            <dt className="col-5 text-muted fw-normal">Semester</dt>
            <dd className="col-7">{profile.semester}</dd>
            <dt className="col-5 text-muted fw-normal">Section</dt>
            <dd className="col-7">{profile.section}</dd>
            <dt className="col-5 text-muted fw-normal">Email</dt>
            <dd className="col-7 text-break">{profile.email}</dd>
          </dl>
        </Card.Body>
      </Card>
      <Link to="/student/scan" className="btn btn-primary mt-3">
        Scan Attendance QR
      </Link>

      {scheduleDay && (
        <Card className="mt-4" style={{ maxWidth: 480 }}>
          <Card.Body>
            <h2 className="h6 mb-3">{scheduleDay}'s Timetable — Section {profile.section}</h2>
            {(() => {
              const mySlots = slots.filter((slot) => slot.section === profile.section);
              return mySlots.length === 0 ? (
                <p className="text-muted mb-0">No training sessions scheduled today.</p>
              ) : (
                <Table size="sm" borderless className="mb-0">
                  <tbody>
                    {mySlots.map((slot, index) => (
                      <tr key={index}>
                        <td className="text-muted font-mono">
                          {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                        </td>
                        <td>{slot.subject}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              );
            })()}
          </Card.Body>
        </Card>
      )}
    </AppShell>
  );
}
