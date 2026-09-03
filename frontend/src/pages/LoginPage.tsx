import { useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Form, Button, Alert, InputGroup, Spinner } from "react-bootstrap";
import { login } from "../api/client";
import logo from "../assets/logo.png";
import Starfield from "../components/Starfield";

// Shared cPanel hosting spins the app down when idle — the first request
// after a while can take several seconds while Passenger cold-starts a
// fresh process. This isn't an error, just worth explaining if it's taking
// a while so the button doesn't look stuck.
const SLOW_LOGIN_HINT_MS = 4000;

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
      const { role } = await login(username, password);
      navigate(role === "teacher" ? "/teacher/profile" : "/student/profile");
    } catch {
      setError("Invalid username or password.");
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
