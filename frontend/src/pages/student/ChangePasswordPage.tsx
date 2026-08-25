import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Form, Button, Alert } from "react-bootstrap";
import { changePassword } from "../../api/client";
import AppShell from "../../components/AppShell";

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }

    setSubmitting(true);
    try {
      await changePassword(oldPassword, newPassword);
      setSuccess(true);
      setTimeout(() => navigate("/student/profile"), 1500);
    } catch (err: any) {
      const data = err?.response?.data;
      const message =
        data?.old_password || data?.new_password?.[0] || data?.detail || "Could not change password.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell>
      <h1 className="h3 mb-4">Change Password</h1>
      <Card style={{ maxWidth: 400 }}>
        <Card.Body>
          {error && <Alert variant="danger">{error}</Alert>}
          {success && <Alert variant="success">Password changed. Redirecting...</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="old-password">
              <Form.Label>Current password</Form.Label>
              <Form.Control
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3" controlId="new-password">
              <Form.Label>New password</Form.Label>
              <Form.Control
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                minLength={8}
                required
              />
              <Form.Text className="text-muted">At least 8 characters.</Form.Text>
            </Form.Group>
            <Form.Group className="mb-3" controlId="confirm-password">
              <Form.Label>Confirm new password</Form.Label>
              <Form.Control
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </Form.Group>
            <Button type="submit" className="w-100" disabled={submitting}>
              {submitting ? "Changing..." : "Change Password"}
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </AppShell>
  );
}
