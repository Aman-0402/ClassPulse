import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Col, Form, ListGroup, Row, Spinner, Table } from "react-bootstrap";
import {
  getTeacherStudentData,
  logout,
  resetStudentPasswordToCrn,
  resetStudentTrustedDevice,
  setProfileScanLock,
} from "../../api/client";
import type { TeacherStudentDataResponse, TeacherStudentSummary } from "../../api/client";
import AppShell from "../../components/AppShell";
import { formatSessionTime } from "../../utils/time";
import { notifySuccess, notifyError } from "../../utils/alerts";

function filterStudents(students: TeacherStudentSummary[], query: string): TeacherStudentSummary[] {
  const q = query.trim().toLowerCase();
  if (!q) return students;
  return students.filter((student) =>
    [student.name, student.crn, student.roll_number, student.email, student.contact_number]
      .some((value) => value.toLowerCase().includes(q))
  );
}

export default function StudentDataPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<TeacherStudentDataResponse | null>(null);
  const [section, setSection] = useState(searchParams.get("section") ?? "");
  const [selectedCrn, setSelectedCrn] = useState(searchParams.get("crn") ?? "");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resettingDevice, setResettingDevice] = useState(false);
  const [savingScanLock, setSavingScanLock] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    setLoading(true);
    getTeacherStudentData(section, selectedCrn)
      .then((result) => {
        if (!active) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load student data.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [navigate, section, selectedCrn]);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (section) params.section = section;
    if (selectedCrn) params.crn = selectedCrn;
    setSearchParams(params, { replace: true });
  }, [section, selectedCrn, setSearchParams]);

  const filteredStudents = useMemo(
    () => filterStudents(data?.students ?? [], query),
    [data?.students, query]
  );
  const effectiveSection = section || data?.section || "";
  const incompleteCount = data?.students.filter((student) => !student.scan_profile_complete).length ?? 0;

  const handleSectionChange = (nextSection: string) => {
    setSection(nextSection);
    setSelectedCrn("");
  };

  const handleResetPassword = async () => {
    if (!data?.selected_student) return;
    const ok = window.confirm(`Reset ${data.selected_student.name}'s password to their CRN (${data.selected_student.crn})?`);
    if (!ok) return;
    setResetting(true);
    try {
      await resetStudentPasswordToCrn(data.selected_student.crn);
      notifySuccess("Password Reset", "The student's password is now their CRN.");
    } catch {
      notifyError("Reset Failed", "Could not reset this student's password.");
    } finally {
      setResetting(false);
    }
  };

  const handleResetDevice = async () => {
    if (!data?.selected_student) return;
    const ok = window.confirm(`Reset trusted device for ${data.selected_student.name}? Their next successful scan will link the new phone.`);
    if (!ok) return;
    setResettingDevice(true);
    try {
      await resetStudentTrustedDevice(data.selected_student.crn);
      const refreshed = await getTeacherStudentData(effectiveSection, data.selected_student.crn);
      setData(refreshed);
      notifySuccess("Device Reset", "The student's next successful scan will link their current phone.");
    } catch {
      notifyError("Reset Failed", "Could not reset this student's trusted device.");
    } finally {
      setResettingDevice(false);
    }
  };

  const handleToggleScanLock = async () => {
    if (!data) return;
    const nextEnabled = !data.profile_scan_lock_enabled;
    setSavingScanLock(true);
    try {
      const result = await setProfileScanLock(nextEnabled);
      setData((prev) => (prev ? { ...prev, profile_scan_lock_enabled: result.profile_scan_lock_enabled } : prev));
      notifySuccess(
        result.profile_scan_lock_enabled ? "Scan Lock Enabled" : "Scan Lock Disabled",
        result.profile_scan_lock_enabled
          ? "Students must add photo, email, and contact number before scanning."
          : "Students can scan attendance even if their profile is incomplete."
      );
    } catch {
      notifyError("Update Failed", "Could not update the student scan lock.");
    } finally {
      setSavingScanLock(false);
    }
  };

  return (
    <AppShell>
      <div className="d-flex justify-content-between align-items-end gap-3 flex-wrap mb-4">
        <div>
          <h1 className="h3 mb-1">Student Data</h1>
          {data && (
            <div className="text-muted small">
              Profile scan lock is {data.profile_scan_lock_enabled ? "enabled" : "disabled"}.
              {incompleteCount > 0 ? ` ${incompleteCount} student${incompleteCount === 1 ? "" : "s"} missing required profile data.` : " All visible students are complete."}
            </div>
          )}
        </div>
        <div className="d-flex gap-2 flex-wrap">
          {data && (
            <Button
              variant={data.profile_scan_lock_enabled ? "danger" : "outline-secondary"}
              onClick={handleToggleScanLock}
              disabled={savingScanLock}
            >
              {savingScanLock
                ? "Saving..."
                : data.profile_scan_lock_enabled
                ? "Disable Scan Lock"
                : "Enable Scan Lock"}
            </Button>
          )}
          <Form.Group controlId="student-data-section" style={{ minWidth: 180 }}>
            <Form.Label className="small text-muted mb-1">Section</Form.Label>
            <Form.Select value={effectiveSection} onChange={(event) => handleSectionChange(event.target.value)}>
              {(data?.sections ?? []).map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group controlId="student-data-search" style={{ minWidth: 240 }}>
            <Form.Label className="small text-muted mb-1">Search</Form.Label>
            <Form.Control
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, CRN, roll no."
            />
          </Form.Group>
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {loading && <Spinner animation="border" />}

      {!loading && data && (
        <Row className="g-4">
          <Col lg={7}>
            <div className="table-responsive">
              <Table striped bordered hover>
                <thead>
                  <tr>
                    <th>CRN</th>
                    <th>Roll No.</th>
                    <th>Name</th>
                    <th>Contact</th>
                    <th>Profile</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStudents.map((student) => (
                    <tr
                      key={student.crn}
                      style={{ cursor: "pointer" }}
                      onClick={() => setSelectedCrn(student.crn)}
                    >
                      <td className="font-mono">{student.crn}</td>
                      <td className="font-mono">{student.roll_number}</td>
                      <td>{student.name}</td>
                      <td className={student.contact_number ? "font-mono" : "text-muted"}>
                        {student.contact_number || "-"}
                      </td>
                      <td>
                        <span className={`stamp ${student.scan_profile_complete ? "stamp-present" : "stamp-absent"}`}>
                          {student.scan_profile_complete ? "Complete" : "Incomplete"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
            {filteredStudents.length === 0 && <p className="text-muted">No students found.</p>}
          </Col>

          <Col lg={5}>
            {!data.selected_student ? (
              <Card>
                <Card.Body>
                  <p className="text-muted mb-0">Click a student name to view full details.</p>
                </Card.Body>
              </Card>
            ) : (
              <Card>
                <Card.Body>
                  <div className="d-flex gap-3 align-items-center mb-3">
                    {data.selected_student.photo ? (
                      <img
                        src={data.selected_student.photo}
                        alt=""
                        width={84}
                        height={84}
                        style={{ borderRadius: 8, objectFit: "cover", border: "2px solid var(--line)" }}
                      />
                    ) : (
                      <span
                        className="d-inline-flex align-items-center justify-content-center flex-shrink-0"
                        style={{
                          width: 84,
                          height: 84,
                          borderRadius: 8,
                          background: "var(--line)",
                          color: "var(--ink-soft)",
                          fontWeight: 700,
                          fontSize: "1.7rem",
                        }}
                      >
                        {data.selected_student.name.charAt(0).toUpperCase()}
                      </span>
                    )}
                    <div>
                      <h2 className="h5 mb-1">{data.selected_student.name}</h2>
                      <div className="font-mono text-muted">{data.selected_student.crn}</div>
                    </div>
                  </div>

                  <div className="d-flex flex-column gap-2 mb-3">
                    <div className="info-row"><span className="info-row-label">Username</span><span className="font-mono">{data.selected_student.username}</span></div>
                    <div className="info-row"><span className="info-row-label">Roll No.</span><span className="font-mono">{data.selected_student.roll_number}</span></div>
                    <div className="info-row"><span className="info-row-label">Section</span><span>{data.selected_student.section}</span></div>
                    <div className="info-row"><span className="info-row-label">Course</span><span>{data.selected_student.course}</span></div>
                    <div className="info-row"><span className="info-row-label">Semester</span><span>{data.selected_student.semester}</span></div>
                    <div className="info-row"><span className="info-row-label">Email</span><span className="text-break">{data.selected_student.email}</span></div>
                    <div className="info-row">
                      <span className="info-row-label">Contact</span>
                      <span>{data.selected_student.contact_number || "Not added"}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">Trusted Device</span>
                      <span>
                        {data.selected_student.trusted_device_bound
                          ? `Linked${data.selected_student.trusted_device_bound_at ? ` on ${data.selected_student.trusted_device_bound_at.slice(0, 10)}` : ""}`
                          : "Not linked yet"}
                      </span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">Scan Profile</span>
                      <span>
                        {data.selected_student.scan_profile_complete
                          ? "Complete"
                          : `Missing ${data.selected_student.missing_scan_profile_fields.join(", ")}`}
                      </span>
                    </div>
                  </div>

                  <Alert variant="warning" className="py-2">
                    {data.selected_student.password_note}
                  </Alert>
                  <Button variant="outline-danger" size="sm" onClick={handleResetPassword} disabled={resetting}>
                    {resetting ? "Resetting..." : "Reset Password to CRN"}
                  </Button>
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    className="ms-2"
                    onClick={handleResetDevice}
                    disabled={resettingDevice}
                  >
                    {resettingDevice ? "Resetting..." : "Reset Trusted Device"}
                  </Button>

                  <h3 className="h6 mt-4">Attendance History</h3>
                  {data.selected_student.attendance.length === 0 ? (
                    <p className="text-muted mb-0">No attendance marked yet.</p>
                  ) : (
                    <ListGroup style={{ maxHeight: 340, overflowY: "auto" }}>
                      {data.selected_student.attendance.map((record, index) => (
                        <ListGroup.Item key={`${record.marked_at}-${index}`}>
                          <div className="d-flex justify-content-between gap-2">
                            <span>{record.subject}</span>
                            <span className="font-mono text-muted">{record.date}</span>
                          </div>
                          <div className="small text-muted">
                            Section {record.section || "-"} - {formatSessionTime(record.marked_at)}
                          </div>
                        </ListGroup.Item>
                      ))}
                    </ListGroup>
                  )}
                </Card.Body>
              </Card>
            )}
          </Col>
        </Row>
      )}
    </AppShell>
  );
}
