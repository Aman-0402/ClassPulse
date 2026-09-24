import { useRef, useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { Form, Button, Alert, InputGroup, Spinner } from "react-bootstrap";
import { login } from "../api/client";
import logo from "../assets/logo.png";
import Starfield from "../components/Starfield";
import { getRememberedUsername, setRememberedUsername } from "../utils/session";

// Shared cPanel hosting spins the app down when idle — the first request
// after a while can take several seconds while Passenger cold-starts a
// fresh process. This isn't an error, just worth explaining if it's taking
// a while so the button doesn't look stuck.
const SLOW_LOGIN_HINT_MS = 4000;

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState(() => getRememberedUsername());
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => Boolean(getRememberedUsername()));
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSlowHint, setShowSlowHint] = useState(false);
  const slowHintTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    setShowSlowHint(false);
    slowHintTimeout.current = setTimeout(() => setShowSlowHint(true), SLOW_LOGIN_HINT_MS);
    try {
      const { role } = await login(username, password, rememberMe);
      setRememberedUsername(username, rememberMe);
      const redirectTo = (location.state as { from?: { pathname?: string; search?: string } } | null)?.from;
      const requestedPath = `${redirectTo?.pathname ?? ""}${redirectTo?.search ?? ""}`;
      const canUseRequestedPath =
        role === "student"
          ? requestedPath.startsWith("/student/")
          : requestedPath.startsWith("/teacher/");
      navigate(canUseRequestedPath ? requestedPath : role === "teacher" ? "/teacher/profile" : "/student/profile", {
        replace: true,
      });
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.response?.data?.non_field_errors?.[0] || "Invalid username or password.");
      setSubmitting(false);
    } finally {
      clearTimeout(slowHintTimeout.current);
    }
    // Deliberately not resetting submitting on success — the page is about
    // to navigate away, and leaving the button in its loading state avoids
    // a flash back to "Log In" right before the route change.
  };

  return (
    <div className="auth-shell">
      <Starfield />
      <div className="auth-card">
        <img src={logo} alt="ClassPulse" className="auth-logo" />
        <h2>Welcome back</h2>
        <a
          href="https://aman-0402.github.io/AI-World/"
          className="btn btn-outline-secondary w-100 mb-3"
        >
          Back to AI World
        </a>
        {error && <Alert variant="danger">{error}</Alert>}
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-2" controlId="login-username">
            <Form.Label>Username</Form.Label>
            <Form.Control
              value={username}
              onChange={(e) => setUsername(e.target.value.trim())}
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              disabled={submitting}
              required
            />
          </Form.Group>
          <Form.Group className="mb-3" controlId="login-password">
            <Form.Label>Password</Form.Label>
            <InputGroup>
              <Form.Control
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
                required
              />
              <Button
                variant="outline-secondary"
                onClick={() => setShowPassword((prev) => !prev)}
                disabled={submitting}
                tabIndex={-1}
              >
                {showPassword ? "Hide" : "Show"}
              </Button>
            </InputGroup>
          </Form.Group>
          <Form.Group className="mb-3" controlId="login-remember">
            <Form.Check
              type="checkbox"
              label="Remember me on this device"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={submitting}
            />
          </Form.Group>
          <Button type="submit" className="w-100" disabled={submitting}>
            {submitting ? (
              <>
                <Spinner as="span" animation="border" size="sm" className="me-2" />
                Logging in...
              </>
            ) : (
              "Log In"
            )}
          </Button>
          {showSlowHint && (
            <p className="text-center text-muted small mt-2 mb-0">
              Still working — the server can take a moment to wake up after being idle.
            </p>
          )}
        </Form>
        <div className="text-center mt-3">
          <Link to="/forgot-password" className="small">
            Forgot password?
          </Link>
        </div>
      </div>
    </div>
  );
}
