import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Navbar, Nav, Button } from "react-bootstrap";
import { logout } from "../api/client";
import logo from "../assets/logo.png";
import InstallPrompt from "./InstallPrompt";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const role = localStorage.getItem("classpulse_role");

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div>
      <Navbar expand="md" variant="dark" className="app-shell-header" collapseOnSelect>
        <Navbar.Brand
          as={Link}
          to={role === "teacher" ? "/teacher/profile" : "/student/profile"}
          className="app-shell-brand"
        >
          <img src={logo} alt="ClassPulse" className="app-shell-logo" />
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="app-shell-nav-collapse" />
        <Navbar.Collapse id="app-shell-nav-collapse">
          <Nav className="app-shell-nav ms-md-auto">
            {role === "teacher" ? (
              <>
                <Link to="/teacher/profile" className="btn btn-outline-light btn-sm">
                  Profile
                </Link>
                <Link to="/teacher/analytics" className="btn btn-outline-light btn-sm">
                  Analytics
                </Link>
                <Link to="/teacher/day-attendance" className="btn btn-outline-light btn-sm">
                  Day-wise
                </Link>
                <Link to="/teacher/otp-history" className="btn btn-outline-light btn-sm">
                  OTP History
                </Link>
              </>
            ) : (
              <>
                <Link to="/student/profile" className="btn btn-outline-light btn-sm">
                  Profile
                </Link>
                <Link to="/student/scan" className="btn btn-outline-light btn-sm">
                  Scan QR
                </Link>
                <Link to="/student/history" className="btn btn-outline-light btn-sm">
                  History
                </Link>
              </>
            )}
            <Button variant="outline-light" size="sm" onClick={handleLogout}>
              Log Out
            </Button>
          </Nav>
        </Navbar.Collapse>
      </Navbar>
      <main className="app-shell-main">{children}</main>
      <InstallPrompt />
    </div>
  );
}
