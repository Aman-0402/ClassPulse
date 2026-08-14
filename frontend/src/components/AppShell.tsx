import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "react-bootstrap";
import { logout } from "../api/client";
import logo from "../assets/logo.png";

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
      <header className="app-shell-header">
        <Link to={role === "teacher" ? "/teacher/profile" : "/student/profile"} className="app-shell-brand">
          <img src={logo} alt="ClassPulse" className="app-shell-logo" />
        </Link>
        <nav className="app-shell-nav">
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
        </nav>
      </header>
      <main className="app-shell-main">{children}</main>
    </div>
  );
}
