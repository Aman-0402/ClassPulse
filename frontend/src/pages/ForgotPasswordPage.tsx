import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Form, Button, Alert, InputGroup } from "react-bootstrap";
import { requestPasswordResetOtp, resetPasswordWithOtp } from "../api/client";
import logo from "../assets/logo.png";
import Starfield from "../components/Starfield";

const RESEND_COOLDOWN_SECONDS = 60;

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"request" | "reset">("request");
  const [username, setUsername] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => setCooldown((prev) => Math.max(0, prev - 1)), 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cooldown > 0) return;
    setError(null);
    setSubmitting(true);
    try {
      await requestPasswordResetOtp(username);
      setStep("reset");
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch {
      setError("Could not request an OTP right now. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }
    setSubmitting(true);
    try {
      await resetPasswordWithOtp(username, otp, newPassword);
      setSuccess("Password reset. Redirecting to login...");
      setTimeout(() => navigate("/login"), 1500);
    } catch (err: any) {
      const data = err?.response?.data;
      const message =
        data?.new_password?.[0] || data?.non_field_errors?.[0] || data?.detail || "Could not reset password.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-shell">
      <Starfield />
      <div className="auth-card">
        <img src={logo} alt="ClassPulse" className="auth-logo" />
        <h2>Forgot Password</h2>
        {error && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        {step === "request" ? (
          <>
            <p className="text-muted small">
              Enter your username to request an OTP. Your admin will have the code — ask them for it once
              you've requested it.
            </p>
            <Form onSubmit={handleRequestOtp}>
              <Form.Group className="mb-3" controlId="forgot-username">
                <Form.Label>Username</Form.Label>
                <Form.Control
                  value={username}
                  onChange={(e) => setUsername(e.target.value.trim().toUpperCase())}
                  autoCapitalize="characters"
                  autoCorrect="off"
                  spellCheck={false}
                  required
                />
              </Form.Group>
              <Button type="submit" className="w-100" disabled={submitting || cooldown > 0}>
                {submitting ? "Requesting..." : cooldown > 0 ? `Resend in ${cooldown}s` : "Request OTP"}
              </Button>
            </Form>
          </>
        ) : (
          <>
            <p className="text-muted small">
              Ask your admin for the OTP they received for <strong>{username}</strong>, then enter it below
              with your new password.
            </p>
            <Form onSubmit={handleReset}>
              <Form.Group className="mb-3" controlId="reset-otp">
                <Form.Label>OTP</Form.Label>
                <Form.Control
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  maxLength={6}
                  inputMode="numeric"
                  placeholder="6-digit code"
                  required
                  autoFocus
                />
              </Form.Group>
              <Form.Group className="mb-3" controlId="reset-new-password">
                <Form.Label>New password</Form.Label>
                <InputGroup>
                  <Form.Control
                    type={showPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                  <Button variant="outline-secondary" tabIndex={-1} onClick={() => setShowPassword((v) => !v)}>
                    {showPassword ? "Hide" : "Show"}
                  </Button>
                </InputGroup>
                <Form.Text className="text-muted">At least 8 characters.</Form.Text>
              </Form.Group>
              <Form.Group className="mb-3" controlId="reset-confirm-password">
                <Form.Label>Confirm new password</Form.Label>
                <Form.Control
                  type={showPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </Form.Group>
              <Button type="submit" className="w-100" disabled={submitting}>
                {submitting ? "Resetting..." : "Reset Password"}
              </Button>
              <Button
                variant="link"
                className="w-100 mt-2"
                onClick={() => setStep("request")}
                disabled={submitting}
              >
                Use a different username / request a new OTP
              </Button>
            </Form>
          </>
        )}

        <div className="text-center mt-3">
          <Link to="/login" className="small">
            Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}
