import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Form, Button, Alert, InputGroup } from "react-bootstrap";
import { changePassword } from "../../api/client";
import AppShell from "../../components/AppShell";

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
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
      <Card style={{ maxWidth: 440 }} className="mx-auto">
        <Card.Body className="p-4">
          {error && <Alert variant="danger">{error}</Alert>}
          {success && (
            <Alert variant="success" className="d-flex align-items-center gap-2">
              <span className="stamp stamp-present">Done</span>
              Password changed. Redirecting...
            </Alert>
          )}
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="old-password">
              <Form.Label>Current password</Form.Label>
              <InputGroup>
                <Form.Control
                  type={showOld ? "text" : "password"}
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                />
                <Button variant="outline-secondary" tabIndex={-1} onClick={() => setShowOld((v) => !v)}>
                  {showOld ? "Hide" : "Show"}
                </Button>
              </InputGroup>
            </Form.Group>
            <Form.Group className="mb-3" controlId="new-password">
              <Form.Label>New password</Form.Label>
              <InputGroup>
                <Form.Control
                  type={showNew ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  minLength={8}
                  required
                />
                <Button variant="outline-secondary" tabIndex={-1} onClick={() => setShowNew((v) => !v)}>
                  {showNew ? "Hide" : "Show"}
                </Button>
              </InputGroup>
              <Form.Text className="text-muted">At least 8 characters.</Form.Text>
            </Form.Group>
            <Form.Group className="mb-4" controlId="confirm-password">
              <Form.Label>Confirm new password</Form.Label>
              <InputGroup>
                <Form.Control
                  type={showConfirm ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
                <Button variant="outline-secondary" tabIndex={-1} onClick={() => setShowConfirm((v) => !v)}>
                  {showConfirm ? "Hide" : "Show"}
                </Button>
              </InputGroup>
            </Form.Group>
            <div className="d-flex gap-2">
              <button
                type="submit"
                className="cta-button flex-grow-1 justify-content-center border-0"
                disabled={submitting}
              >
                {submitting ? "Changing..." : "Change Password"}
              </button>
              <Link to="/student/profile" className="btn btn-outline-secondary">
                Cancel
              </Link>
            </div>
          </Form>
        </Card.Body>
      </Card>
    </AppShell>
  );
}
