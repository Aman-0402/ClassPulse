import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Card, Form, Modal, Spinner, Table } from "react-bootstrap";
import {
  getAnalytics,
  getDayAttendance,
  logout,
  markNotAttending,
  setManualAttendance,
  unmarkNotAttending,
} from "../../api/client";
import type { DayAttendanceResponse, DayAttendanceStudent } from "../../api/client";
import AppShell from "../../components/AppShell";
import PageHeader from "../../components/PageHeader";
import TablePagination from "../../components/TablePagination";
import { formatSessionTime } from "../../utils/time";
import { notifyError, notifySuccess } from "../../utils/alerts";

const PAGE_SIZE = 70;

// Same quote-prefix guard the backend's CSV/Excel exports use (sanitize_report_cell
// in attendance/services.py) — CRN/name are free-text via student profile-edit
// requests, so a value starting with =/+/-/@ could execute as a formula if opened
// in Excel/Sheets unescaped (CWE-1236). This export is generated client-side (the
// data's already fully loaded here), so it needs its own copy of the same guard.
function sanitizeCell(value: string): string {
  return /^[=+\-@]/.test(value) ? `'${value}` : value;
}

type StatusFilter = "all" | "present" | "absent" | "not_attending";

const STATUS_FILTER_LABEL: Record<StatusFilter, string> = {
  all: "",
  present: "present",
  absent: "absent",
  not_attending: "not attending",
};

function statusLabel(s: DayAttendanceStudent): "Present" | "Absent" | "Not Attending" {
  if (s.present) return "Present";
  if (s.not_attending) return "Not Attending";
  return "Absent";
}

function filterByStatus(students: DayAttendanceStudent[], statusFilter: StatusFilter): DayAttendanceStudent[] {
  switch (statusFilter) {
    case "present":
      return students.filter((s) => s.present);
    case "not_attending":
      return students.filter((s) => s.not_attending);
    case "absent":
      // "Absent only" means plain unexplained absences — not attending has its own filter.
      return students.filter((s) => !s.present && !s.not_attending);
    default:
      return students;
  }
}

function downloadCsv(filename: string, rows: string[][]) {
  const csv = rows.map((row) => row.map((cell) => `"${sanitizeCell(cell).replace(/"/g, '""')}"`).join(",")).join("\r\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function todayIsoDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function formatPromptDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${day}-${month}-${year}`;
}

function buildErpPrompt(section: string, date: string, presentStudents: DayAttendanceStudent[]): string {
  const list = presentStudents.map((student) => `${student.crn} — ${student.name}`).join("\n");
  return `Go to the ERP attendance module and mark attendance for Section ${section}, dated ${formatPromptDate(date)}.

Open the daily attendance / class attendance marking page for this section and date. For each student below, set their status to "Present" (match by CRN first; if CRN isn't visible, match by Name). Leave any student NOT in this list as "Absent" (or the ERP's default).

Present students (CRN — Name):
${list}

Total: ${presentStudents.length} present.

Before submitting: show me a summary of which students got checked as Present and flag any CRN you couldn't find on the page, so I can confirm before you click submit/save.`;
}

export default function DayAttendancePage() {
  const [sections, setSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [date, setDate] = useState(todayIsoDate());
  const [data, setData] = useState<DayAttendanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingCrn, setSavingCrn] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [promptText, setPromptText] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getAnalytics()
      .then((result) => {
        setSections(result.available_sections);
        if (result.available_sections.length > 0) {
          setSection(result.available_sections[0]);
        }
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        }
      });
  }, [navigate]);

  useEffect(() => {
    if (!section || !date) return;
    let active = true;
    setLoading(true);
    getDayAttendance(section, date)
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (!active) return;
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load attendance for this date.");
          setData(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [section, date, navigate]);

  useEffect(() => {
    setPage(1);
  }, [section, date, statusFilter]);

  const handleExport = () => {
    if (!data) return;
    const filtered = filterByStatus(data.students, statusFilter);
    const rows: string[][] = [
      ["S.No", "CRN", "Roll No.", "Name", "Status"],
      ...filtered.map((s, index) => [
        String(index + 1),
        s.crn,
        s.roll_number,
        s.name,
        statusLabel(s),
      ]),
    ];
    const suffix = statusFilter === "all" ? "" : `_${statusFilter}`;
    downloadCsv(`day_attendance_${section}_${date}${suffix}.csv`, rows);
  };

  const handleCreatePrompt = async () => {
    if (!data) return;
    const presentStudents = data.students.filter((student) => student.present);
    if (presentStudents.length === 0) {
      notifyError("No Present Students", "There are no present students for this section and date.");
      return;
    }
    const prompt = buildErpPrompt(data.section, data.date, presentStudents);
    setPromptText(prompt);
    setShowPrompt(true);
    try {
      await navigator.clipboard.writeText(prompt);
      notifySuccess("Prompt Copied", "The ERP attendance prompt was copied to your clipboard.");
    } catch {
      notifySuccess("Prompt Ready", "Copy the prompt from the preview box.");
    }
  };

  const canToggle = data?.sessions.length === 1;

  const handleToggle = async (crn: string, currentlyPresent: boolean) => {
    if (!canToggle || !data) return;
    const sessionId = data.sessions[0].id;
    setSavingCrn(crn);
    setSaveError(null);
    try {
      await setManualAttendance(sessionId, crn, !currentlyPresent);
      const refreshed = await getDayAttendance(section, date);
      setData(refreshed);
    } catch {
      setSaveError("Could not update attendance. Please try again.");
    } finally {
      setSavingCrn(null);
    }
  };

  // Not-attending isn't tied to a session, so it works even on a day with
  // more than one session (unlike the present/absent toggle above).
  const handleMarkNotAttending = async (crn: string) => {
    setSavingCrn(crn);
    setSaveError(null);
    try {
      await markNotAttending(crn, section, date);
      setData(await getDayAttendance(section, date));
    } catch {
      setSaveError("Could not mark that student as not attending. Please try again.");
    } finally {
      setSavingCrn(null);
    }
  };

  const handleUnmarkNotAttending = async (crn: string) => {
    setSavingCrn(crn);
    setSaveError(null);
    try {
      await unmarkNotAttending(crn, section, date);
      setData(await getDayAttendance(section, date));
    } catch {
      setSaveError("Could not undo that. Please try again.");
    } finally {
      setSavingCrn(null);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Teacher"
        title="Day-wise Attendance"
        subtitle="Who was present on a given day."
        actions={
        <div className="d-flex gap-2 flex-wrap">
          <Form.Group controlId="day-section" style={{ minWidth: 180 }}>
            <Form.Label className="small text-muted mb-1">Section</Form.Label>
            <Form.Select value={section} onChange={(e) => setSection(e.target.value)}>
              {sections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group controlId="day-date" style={{ minWidth: 170 }}>
            <Form.Label className="small text-muted mb-1">Date</Form.Label>
            <Form.Control type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Form.Group>
          <Form.Group controlId="day-status" style={{ minWidth: 160 }}>
            <Form.Label className="small text-muted mb-1">Status</Form.Label>
            <Form.Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            >
              <option value="all">All</option>
              <option value="present">Present only</option>
              <option value="absent">Absent only</option>
              <option value="not_attending">Not attending only</option>
            </Form.Select>
          </Form.Group>
        </div>
        }
      />

      {error && <Alert variant="danger">{error}</Alert>}

      {loading && <Spinner animation="border" />}

      {!loading && data && (
        <>
          <Card className="mb-4 stat-strip">
            <Card.Body className="d-flex justify-content-between align-items-center">
              <div>
                <div className="text-muted small">Present</div>
                <div className="fs-4 font-mono">
                  {data.present_count} / {data.total_students}
                </div>
              </div>
              {data.sessions.length === 0 ? (
                <span className="stamp stamp-neutral">No session this day</span>
              ) : (
                <span className="stamp stamp-neutral">
                  {data.sessions.map((s) => formatSessionTime(s.start_time)).join(", ")}
                </span>
              )}
            </Card.Body>
          </Card>

          {saveError && <Alert variant="danger">{saveError}</Alert>}

          {data.sessions.length > 1 && (
            <p className="text-muted small">
              Multiple sessions this day — manual correction is disabled to avoid ambiguity. Use the exports on
              Analytics for a full breakdown.
            </p>
          )}

          {data.students.length === 0 ? (
            <p className="text-muted">No students in this section.</p>
          ) : (
            (() => {
              const filteredStudents = filterByStatus(data.students, statusFilter);
              if (filteredStudents.length === 0) {
                return <p className="text-muted">No {STATUS_FILTER_LABEL[statusFilter]} students for this date.</p>;
              }
              const totalPages = Math.max(1, Math.ceil(filteredStudents.length / PAGE_SIZE));
              const pageStudents = filteredStudents.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
              return (
                <>
                  <div className="d-flex gap-2 flex-wrap mb-2">
                    <Button variant="outline-secondary" size="sm" onClick={handleExport}>
                      Export CSV{statusFilter !== "all" ? ` (${STATUS_FILTER_LABEL[statusFilter]} only)` : ""}
                    </Button>
                    <Button variant="outline-primary" size="sm" onClick={handleCreatePrompt}>
                      Create Prompt
                    </Button>
                  </div>
                  <div className="table-responsive">
                    <Table striped bordered>
                      <thead>
                        <tr>
                          <th>S.No</th>
                          <th>CRN</th>
                          <th>Roll No.</th>
                          <th>Name</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pageStudents.map((s, index) => (
                          <tr key={s.crn}>
                            <td>{(page - 1) * PAGE_SIZE + index + 1}</td>
                            <td className="font-mono">{s.crn}</td>
                            <td className="font-mono">{s.roll_number}</td>
                            <td>{s.name}</td>
                            <td>
                              <div className="d-flex align-items-center gap-2 flex-wrap">
                                <button
                                  type="button"
                                  className={`stamp ${
                                    s.present
                                      ? "stamp-present"
                                      : s.not_attending
                                      ? "stamp-not-attending"
                                      : "stamp-absent"
                                  }`}
                                  style={{
                                    border: "none",
                                    cursor: canToggle ? "pointer" : "default",
                                    opacity: savingCrn === s.crn ? 0.5 : 1,
                                  }}
                                  disabled={!canToggle || savingCrn !== null}
                                  title={
                                    canToggle
                                      ? "Click to toggle present/absent"
                                      : "Only editable when there's exactly one session this day"
                                  }
                                  onClick={() => handleToggle(s.crn, s.present)}
                                >
                                  {savingCrn === s.crn ? "Saving..." : statusLabel(s)}
                                </button>
                                {!s.present &&
                                  (s.not_attending ? (
                                    <button
                                      type="button"
                                      className="day-not-attending-link"
                                      disabled={savingCrn !== null}
                                      onClick={() => handleUnmarkNotAttending(s.crn)}
                                    >
                                      Undo
                                    </button>
                                  ) : (
                                    <button
                                      type="button"
                                      className="day-not-attending-link"
                                      disabled={savingCrn !== null}
                                      onClick={() => handleMarkNotAttending(s.crn)}
                                    >
                                      Mark not attending
                                    </button>
                                  ))}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  </div>
                  <TablePagination page={page} totalPages={totalPages} onPageChange={setPage} />
                </>
              );
            })()
          )}
        </>
      )}
      <Modal show={showPrompt} onHide={() => setShowPrompt(false)} size="lg" centered>
        <Modal.Header closeButton>
          <Modal.Title className="h5">ERP Attendance Prompt</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Control
            as="textarea"
            rows={16}
            value={promptText}
            readOnly
            className="font-mono"
          />
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="outline-secondary"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(promptText);
                notifySuccess("Copied", "Prompt copied to clipboard.");
              } catch {
                notifyError("Copy Failed", "Select the text and copy it manually.");
              }
            }}
          >
            Copy Prompt
          </Button>
          <Button onClick={() => setShowPrompt(false)}>Done</Button>
        </Modal.Footer>
      </Modal>
    </AppShell>
  );
}
