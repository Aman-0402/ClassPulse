import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Form, Button, Alert } from "react-bootstrap";
import { registerStudent } from "../api/client";
import logo from "../assets/logo.png";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "", email: "", password: "", first_name: "",
    crn: "", course: "", semester: 1, section: "",
  });
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: name === "semester" ? Number(value) : value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await registerStudent(form);
      navigate("/login");
    } catch (err: any) {
      const data = err?.response?.data;
      setError(data?.crn?.[0] || data?.username?.[0] || "Registration failed.");
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card" style={{ maxWidth: 480 }}>
        <img src={logo} alt="ClassPulse" className="auth-logo" />
        <h2>Student Registration</h2>
        {error && <Alert variant="danger">{error}</Alert>}
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-2" controlId="reg-first-name">
            <Form.Label>Full Name</Form.Label>
            <Form.Control name="first_name" value={form.first_name} onChange={handleChange} required />
          </Form.Group>
          <Form.Group className="mb-2" controlId="reg-username">
            <Form.Label>Username</Form.Label>
            <Form.Control name="username" value={form.username} onChange={handleChange} required />
          </Form.Group>
          <Form.Group className="mb-2" controlId="reg-crn">
            <Form.Label>CRN</Form.Label>
            <Form.Control name="crn" value={form.crn} onChange={handleChange} required />
          </Form.Group>
          <Form.Group className="mb-2" controlId="reg-course">
            <Form.Label>Course</Form.Label>
            <Form.Control name="course" value={form.course} onChange={handleChange} required />
          </Form.Group>
          <Form.Group className="mb-2" controlId="reg-semester">
            <Form.Label>Semester</Form.Label>
            <Form.Control
              type="number"
              name="semester"
              min={1}
              max={12}
              value={form.semester}
              onChange={handleChange}
              required
            />
          </Form.Group>
          <Form.Group className="mb-2" controlId="reg-section">
            <Form.Label>Section</Form.Label>
            <Form.Control name="section" value={form.section} onChange={handleChange} required />
          </Form.Group>
          <Form.Group className="mb-2" controlId="reg-email">
            <Form.Label>Email</Form.Label>
            <Form.Control type="email" name="email" value={form.email} onChange={handleChange} required />
          </Form.Group>
          <Form.Group className="mb-3" controlId="reg-password">
            <Form.Label>Password</Form.Label>
            <Form.Control
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={8}
            />
          </Form.Group>
          <Button type="submit" className="w-100">
            Register
          </Button>
        </Form>
        <p className="text-center mt-3 mb-0 text-muted">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
