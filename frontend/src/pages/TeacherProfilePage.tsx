import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Spinner } from "react-bootstrap";
import { getTeacherProfile, logout } from "../api/client";
import AppShell from "../components/AppShell";

interface TeacherProfile {
  full_name: string;
  email: string;
  username: string;
}

export default function TeacherProfilePage() {
  const [profile, setProfile] = useState<TeacherProfile | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getTeacherProfile()
      .then(setProfile)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
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
    </AppShell>
  );
}
