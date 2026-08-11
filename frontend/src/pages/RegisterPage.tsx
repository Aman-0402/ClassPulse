import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Button, Container, Alert } from "react-bootstrap";
import { registerStudent } from "../api/client";

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
    <Container className="py-4" style={{ maxWidth: 480 }}>
      <h2>Student Registration</h2>
      {error && <Alert variant="danger">{error}</Alert>}
      <Form onSubmit={handleSubmit}>
        <Form.Group className="mb-2">
          <Form.Label>Full Name</Form.Label>
          <Form.Control name="first_name" value={form.first_name} onChange={handleChange} required />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Username</Form.Label>
          <Form.Control name="username" value={form.username} onChange={handleChange} required />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>CRN</Form.Label>
          <Form.Control name="crn" value={form.crn} onChange={handleChange} required />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Course</Form.Label>
          <Form.Control name="course" value={form.course} onChange={handleChange} required />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Semester</Form.Label>
          <Form.Control type="number" name="semester" value={form.semester} onChange={handleChange} required />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Section</Form.Label>
          <Form.Control name="section" value={form.section} onChange={handleChange} required />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Email</Form.Label>
          <Form.Control type="email" name="email" value={form.email} onChange={handleChange} required />
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label>Password</Form.Label>
          <Form.Control type="password" name="password" value={form.password} onChange={handleChange} required minLength={8} />
        </Form.Group>
        <Button type="submit">Register</Button>
      </Form>
    </Container>
  );
}
