import { useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Navbar, Nav, Button, Dropdown } from "react-bootstrap";
import { requestLogout } from "../api/client";
import { notifyInfo } from "../utils/alerts";
import logo from "../assets/logo.png";
import InstallPrompt from "./InstallPrompt";

interface AppShellProps {
  children: ReactNode;
}

interface NavGroupProps {
  label: string;
  items: { to: string; label: string }[];
  onNavigate: () => void;
}

// One dropdown button grouping related links — keeps the bar from growing a
// new button every time a feature is added (it was 11 buttons wide before this).
function NavGroup({ label, items, onNavigate }: NavGroupProps) {
  return (
    <Dropdown>
      <Dropdown.Toggle as={Button} variant="outline-light" size="sm">
        {label}
      </Dropdown.Toggle>
      <Dropdown.Menu>
        {items.map((item) => (
          <Dropdown.Item key={item.to} as={Link} to={item.to} onClick={onNavigate}>
            {item.label}
          </Dropdown.Item>
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
}

export default function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const role = localStorage.getItem("classpulse_role");
  const [expanded, setExpanded] = useState(false);
  const closeMenu = () => setExpanded(false);

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
      <Navbar expand="md" variant="dark" className="app-shell-header" expanded={expanded} onToggle={setExpanded}>
        <Navbar.Brand
          as={Link}
          to={role === "teacher" ? "/teacher/profile" : "/student/profile"}
          className="app-shell-brand"
          onClick={closeMenu}
        >
          <img src={logo} alt="ClassPulse" className="app-shell-logo" />
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="app-shell-nav-collapse" />
        <Navbar.Collapse id="app-shell-nav-collapse">
          <Nav className="app-shell-nav ms-md-auto">
            {role === "teacher" ? (
              <>
                <Link to="/teacher/profile" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  Profile
                </Link>
                <NavGroup
                  label="Attendance"
                  onNavigate={closeMenu}
                  items={[
                    { to: "/teacher/analytics", label: "Analytics" },
                    { to: "/teacher/students", label: "Student Data" },
                    { to: "/teacher/timetable", label: "Timetable" },
                  ]}
                />
                <Link to="/teacher/day-attendance" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  Day-wise
                </Link>
                <NavGroup
                  label="Tasks & Exams"
                  onNavigate={closeMenu}
                  items={[
                    { to: "/teacher/tasks", label: "Tasks" },
                    { to: "/teacher/question-bank", label: "Question Bank" },
                    { to: "/teacher/exams", label: "Exams" },
                    { to: "/syllabus", label: "Syllabus" },
                  ]}
                />
                <NavGroup
                  label="Records"
                  onNavigate={closeMenu}
                  items={[
                    { to: "/teacher/corrections", label: "Profile Corrections" },
                    { to: "/teacher/otp-history", label: "Password Reset OTP History" },
                  ]}
                />
              </>
            ) : (
              <>
                <Link to="/student/profile" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  Profile
                </Link>
                <Link to="/student/scan" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  Scan QR
                </Link>
                <Link to="/student/history" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  History
                </Link>
                <Link to="/student/tasks" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  Tasks
                </Link>
                <Link to="/student/exams" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  Exams
                </Link>
                <Link to="/syllabus" className="btn btn-outline-light btn-sm" onClick={closeMenu}>
                  Syllabus
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
