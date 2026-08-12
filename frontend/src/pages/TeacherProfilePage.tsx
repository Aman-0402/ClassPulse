import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Container, Spinner } from "react-bootstrap";
import { getTeacherProfile, logout } from "../api/client";

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

  if (!profile) return <Spinner animation="border" className="m-4" />;

  return (
    <Container className="py-4">
      <h2>Welcome, {profile.full_name || profile.username}</h2>
      <p>Email: {profile.email}</p>
      <Link to="/teacher/start-attendance" className="btn btn-primary">
        Start Attendance
      </Link>
      <Link to="/teacher/analytics" className="btn btn-outline-primary ms-2">
        Analytics
      </Link>
    </Container>
  );
}
