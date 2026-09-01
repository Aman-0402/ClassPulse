import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Form, Button, Alert, InputGroup } from "react-bootstrap";
import { login } from "../api/client";
import logo from "../assets/logo.png";
import Starfield from "../components/Starfield";

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const { role } = await login(username, password);
      navigate(role === "teacher" ? "/teacher/profile" : "/student/profile");
    } catch {
      setError("Invalid username or password.");
    }
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
            <Form.Control value={username} onChange={(e) => setUsername(e.target.value)} required />
          </Form.Group>
          <Form.Group className="mb-3" controlId="login-password">
            <Form.Label>Password</Form.Label>
            <InputGroup>
              <Form.Control
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Button
                variant="outline-secondary"
                onClick={() => setShowPassword((prev) => !prev)}
                tabIndex={-1}
              >
                {showPassword ? "Hide" : "Show"}
              </Button>
            </InputGroup>
          </Form.Group>
          <Button type="submit" className="w-100">
            Log In
          </Button>
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
