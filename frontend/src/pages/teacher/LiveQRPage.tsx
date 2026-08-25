import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Spinner, Alert, ListGroup, Modal, Table, Toast, ToastContainer, Row, Col } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, getSessionLive, stopSession, getSessionActivity } from "../../api/client";
import type { AttendanceRecord, ActivityLogEntry, DayAttendanceStudent } from "../../api/client";
import AppShell from "../../components/AppShell";

const QR_REFRESH_MS = 15000;
const LIVE_POLL_MS = 3000;

const ACTIVITY_LABELS: Record<ActivityLogEntry["activity_type"], { label: string; stampClass: string }> = {
  duplicate: { label: "Duplicate scan", stampClass: "stamp-absent" },
  expired_token: { label: "Expired QR", stampClass: "stamp-absent" },
  invalid_token: { label: "Invalid QR", stampClass: "stamp-absent" },
  session_closed: { label: "Closed-session attempt", stampClass: "stamp-neutral" },
  new_device: { label: "New device", stampClass: "stamp-neutral" },
  wrong_section: { label: "Wrong section", stampClass: "stamp-absent" },
};

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);
  const [qrRefreshAt, setQrRefreshAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [presentCount, setPresentCount] = useState(0);
  const [recent, setRecent] = useState<AttendanceRecord[]>([]);
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [toastVariant, setToastVariant] = useState<"success" | "warning">("success");
  const [toastKey, setToastKey] = useState(0);
  const [closesAt, setClosesAt] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<"active" | "closed" | null>(null);
  const [sessionSection, setSessionSection] = useState("");
  const [roster, setRoster] = useState<DayAttendanceStudent[]>([]);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [nowTick, setNowTick] = useState(() => Date.now());

  // Tracks which crns/activity entries have already triggered a toast, so re-polling
  // the same data (nothing new happened) never re-announces it. Refs, not state —
  // this bookkeeping shouldn't itself trigger a re-render.
  const seenAttendanceCrns = useRef<Set<string>>(new Set());
  const seenActivityKeys = useRef<Set<string>>(new Set());
  const firstLivePoll = useRef(true);

  useEffect(() => {
    const interval = setInterval(() => setNowTick(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    let active = true;

    const fetchToken = () => {
      getSessionQR(id)
        .then((data) => {
          if (active) {
            setToken(data.token);
            setQrRefreshAt(Date.now() + QR_REFRESH_MS);
            setError(null);
          }
        })
        .catch(() => {
          if (active) setError("Could not refresh the QR code. The session may have ended.");
        });
    };
    fetchToken();
    const interval = setInterval(fetchToken, QR_REFRESH_MS);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    let active = true;

    const pollLive = () => {
      getSessionLive(id)
        .then((data) => {
          if (!active) return;
          setPresentCount(data.present_count);
          setClosesAt(data.closes_at);
          setSessionStatus(data.status);
          setSessionSection(data.section);
          setRoster(data.roster);
          setError(null);

          // Toast only for scans this page hasn't already announced — on the very
          // first poll everything is "new" but shouldn't toast (it's history, not
          // something that just happened).
          if (!firstLivePoll.current) {
            for (const record of data.recent) {
              const key = `${record.crn}-${record.marked_at}`;
              if (!seenAttendanceCrns.current.has(key)) {
                seenAttendanceCrns.current.add(key);
                setToastVariant("success");
                setToast(`${record.name} marked present`);
                setToastKey((k) => k + 1);
              }
            }
          } else {
            for (const record of data.recent) {
              seenAttendanceCrns.current.add(`${record.crn}-${record.marked_at}`);
            }
          }
          setRecent(data.recent);
          firstLivePoll.current = false;
        })
        .catch(() => {
          if (active) setError("Could not load live attendance data.");
        });

      getSessionActivity(id)
        .then((data) => {
          if (!active) return;
          for (const entry of data.logs) {
            const key = `${entry.activity_type}-${entry.student}-${entry.created_at}`;
            if (!seenActivityKeys.current.has(key)) {
              seenActivityKeys.current.add(key);
              if (entry.activity_type === "wrong_section") {
                setToastVariant("warning");
                setToast(`${entry.student} scanned this QR but isn't in this session's section`);
                setToastKey((k) => k + 1);
              }
            }
          }
          setActivityLog(data.logs);
          setActivityError(null);
        })
        .catch(() => {
          // Security panel — an empty list must never be confused with "checked, nothing found."
          if (active) setActivityError("Could not load suspicious activity.");
        });
    };

    pollLive();
    const interval = setInterval(pollLive, LIVE_POLL_MS);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [sessionId]);

  const qrSecondsLeft = qrRefreshAt
    ? Math.max(0, Math.min(QR_REFRESH_MS / 1000, Math.ceil((qrRefreshAt - nowTick) / 1000)))
    : null;

  const windowClosed = sessionStatus === "closed" || (!!closesAt && new Date(closesAt).getTime() <= nowTick);
  const secondsLeft = closesAt ? Math.max(0, Math.floor((new Date(closesAt).getTime() - nowTick) / 1000)) : null;
  const countdownLabel =
    secondsLeft === null ? null : `${String(Math.floor(secondsLeft / 60)).padStart(2, "0")}:${String(secondsLeft % 60).padStart(2, "0")}`;

  const handleConfirmStop = async () => {
    if (!sessionId) return;
    setStopping(true);
    try {
      await stopSession(Number(sessionId));
    } catch {
      // Already closed or some other failure — either way, nothing more to do here.
    }
    navigate("/teacher/profile");
  };

  return (
    <AppShell>
      <h1 className="h3 text-center mb-1">Attendance Live</h1>
      {error && (
        <Alert variant="warning" className="mt-3">
          {error}
        </Alert>
      )}
      <Row className="mt-3">
        <Col md={6} className="text-center">
          {!error && (token ? <QRCodeSVG value={token} size={256} /> : <Spinner animation="border" />)}
          <p className="mt-3 text-muted">
            QR refreshes in <span className="font-mono">{qrSecondsLeft ?? "--"}</span>s
          </p>
        </Col>
        <Col md={6}>
          <div className="d-flex align-items-center gap-2 mb-3 flex-wrap">
            <span className="text-muted">Present:</span>
            <span className="stamp stamp-present">{presentCount}</span>
            {windowClosed ? (
              <span className="stamp stamp-absent">Window closed</span>
            ) : (
              countdownLabel && <span className="stamp stamp-neutral font-mono">{countdownLabel} left</span>
            )}
          </div>
          {recent.length === 0 ? (
            <p className="text-muted">Waiting for students to scan...</p>
          ) : (
            <ListGroup>
              {recent.map((record, index) => (
                <ListGroup.Item
                  key={`${record.crn}-${record.marked_at}-${index}`}
                  className="d-flex align-items-center gap-2"
                >
                  {record.photo ? (
                    <img
                      src={record.photo}
                      alt=""
                      width={40}
                      height={40}
                      style={{ borderRadius: "50%", objectFit: "cover", border: "2px solid var(--line)" }}
                    />
                  ) : (
                    <span
                      className="d-inline-flex align-items-center justify-content-center"
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: "50%",
                        background: "var(--line)",
                        color: "var(--ink-soft)",
                        fontWeight: 700,
                      }}
                    >
                      {record.name.charAt(0).toUpperCase()}
                    </span>
                  )}
                  <span>
                    {record.name} <span className="text-muted font-mono">({record.crn})</span>
                  </span>
                </ListGroup.Item>
              ))}
            </ListGroup>
          )}
        </Col>
      </Row>
      <div className="text-center mt-3 mb-2">
        <Button variant="danger" onClick={() => setShowStopConfirm(true)}>
          Stop Attendance
        </Button>
      </div>
      {roster.length > 0 && (
        <div className="mt-4">
          <h2 className="h5">
            Section {sessionSection} Roster
            <span className="text-muted small ms-2">
              ({roster.filter((s) => s.present).length}/{roster.length} present)
            </span>
          </h2>
          <Table size="sm" striped bordered>
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
              {roster.map((s, index) => (
                <tr key={s.crn}>
                  <td>{index + 1}</td>
                  <td className="font-mono">{s.crn}</td>
                  <td className="font-mono">{s.roll_number}</td>
                  <td>{s.name}</td>
                  <td>
                    <span className={`stamp ${s.present ? "stamp-present" : "stamp-absent"}`}>
                      {s.present ? "Present" : "Absent"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
      {(activityLog.length > 0 || activityError) && (
        <div className="mt-4">
          <h2 className="h5">Suspicious Activity</h2>
          {activityError && <Alert variant="warning">{activityError}</Alert>}
          <ListGroup>
            {activityLog.map((entry, index) => {
              const meta = ACTIVITY_LABELS[entry.activity_type] ?? { label: entry.activity_type, stampClass: "stamp-neutral" };
              return (
                <ListGroup.Item key={`${entry.student}-${entry.created_at}-${index}`}>
                  <span className={`stamp ${meta.stampClass} me-2`}>{meta.label}</span>
                  {entry.student}
                </ListGroup.Item>
              );
            })}
          </ListGroup>
        </div>
      )}

      <Modal show={showStopConfirm} onHide={() => setShowStopConfirm(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title className="h5">Submit attendance?</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          Stopping will close this session for good — no more students can mark attendance after
          this. {presentCount} of {roster.length || "?"} students are currently marked present.
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setShowStopConfirm(false)} disabled={stopping}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleConfirmStop} disabled={stopping}>
            {stopping ? "Submitting..." : "Submit Attendance"}
          </Button>
        </Modal.Footer>
      </Modal>

      <ToastContainer position="top-end" className="p-3">
        <Toast
          key={toastKey}
          show={!!toast}
          onClose={() => setToast(null)}
          delay={toastVariant === "warning" ? 5000 : 3000}
          autohide
          bg={toastVariant}
        >
          <Toast.Body className="text-white d-flex align-items-center gap-2">
            <span className="stamp stamp-animated" style={{ borderColor: "#fff", color: "#fff" }}>
              {toastVariant === "warning" ? "Wrong section" : "Present"}
            </span>
            {toast}
          </Toast.Body>
        </Toast>
      </ToastContainer>
    </AppShell>
  );
}
