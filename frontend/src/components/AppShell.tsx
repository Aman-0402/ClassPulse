import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Navbar, Nav, Button } from "react-bootstrap";
import { requestLogout } from "../api/client";
import { notifyInfo } from "../utils/alerts";
import logo from "../assets/logo.png";
import InstallPrompt from "./InstallPrompt";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const role = localStorage.getItem("classpulse_role");

  const handleLogout = async () => {
    const blocked = await requestLogout();
    if (blocked) {
      notifyInfo("Can't Log Out Yet", blocked);
      return;
    }
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
                <Link to="/teacher/students" className="btn btn-outline-light btn-sm">
                  Student Data
                </Link>
                <Link to="/teacher/timetable" className="btn btn-outline-light btn-sm">
                  Timetable
                </Link>
                <Link to="/teacher/tasks" className="btn btn-outline-light btn-sm">
                  Tasks
                </Link>
                <Link to="/teacher/question-bank" className="btn btn-outline-light btn-sm">
                  Question Bank
                </Link>
                <Link to="/teacher/exams" className="btn btn-outline-light btn-sm">
                  Exams
                </Link>
                <Link to="/teacher/corrections" className="btn btn-outline-light btn-sm">
                  Corrections
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
                <Link to="/student/tasks" className="btn btn-outline-light btn-sm">
                  Tasks
                </Link>
                <Link to="/student/exams" className="btn btn-outline-light btn-sm">
                  Exams
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
