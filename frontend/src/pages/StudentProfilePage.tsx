import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Spinner } from "react-bootstrap";
import { getStudentProfile, logout } from "../api/client";

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
  const navigate = useNavigate();

  useEffect(() => {
    getStudentProfile()
      .then(setProfile)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  if (!profile) return <Spinner animation="border" className="m-4" />;

  return (
    <Container className="py-4">
      <h2>Welcome, {profile.full_name}</h2>
      <p>CRN: {profile.crn}</p>
      <p>Course: {profile.course}</p>
      <p>Semester: {profile.semester}</p>
      <p>Section: {profile.section}</p>
      <p>Email: {profile.email}</p>
    </Container>
  );
}
