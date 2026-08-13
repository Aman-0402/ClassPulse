import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Spinner, Alert, ListGroup, Toast, ToastContainer, Row, Col } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, getSessionLive, stopSession, getSessionActivity } from "../../api/client";
import type { AttendanceRecord, ActivityLogEntry } from "../../api/client";
import { connectToAttendanceSocket } from "../../api/ws";
import type { AttendanceUpdateEvent, ActivityUpdateEvent } from "../../api/ws";
import AppShell from "../../components/AppShell";

const QR_REFRESH_MS = 15000;

const ACTIVITY_LABELS: Record<ActivityLogEntry["activity_type"], { label: string; stampClass: string }> = {
  duplicate: { label: "Duplicate scan", stampClass: "stamp-absent" },
  expired_token: { label: "Expired QR", stampClass: "stamp-absent" },
  invalid_token: { label: "Invalid QR", stampClass: "stamp-absent" },
  session_closed: { label: "Closed-session attempt", stampClass: "stamp-neutral" },
  new_device: { label: "New device", stampClass: "stamp-neutral" },
};

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [presentCount, setPresentCount] = useState(0);
  const [recent, setRecent] = useState<AttendanceRecord[]>([]);
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [toastKey, setToastKey] = useState(0);
  const [wsStatus, setWsStatus] = useState<"connected" | "disconnected" | "reconnecting">("connected");

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    let active = true;

    const fetchToken = () => {
      getSessionQR(id)
        .then((data) => {
          if (active) {
            setToken(data.token);
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

    getSessionLive(id)
      .then((data) => {
        if (active) {
          setPresentCount(data.present_count);
          setRecent(data.recent);
        }
      })
      .catch(() => {
        if (active) setError("Could not load live attendance data.");
      });

    getSessionActivity(id)
      .then((data) => {
        if (active) {
          setActivityLog(data.logs);
          setActivityError(null);
        }
      })
      .catch(() => {
        // Security panel — an empty list must never be confused with "checked, nothing found."
        if (active) setActivityError("Could not load suspicious activity.");
      });

    const handle = connectToAttendanceSocket(id, {
      onUpdate: (update: AttendanceUpdateEvent) => {
        if (!active) return;
        setPresentCount(update.present_count);
        setRecent((prev) => [{ name: update.name, crn: update.crn, marked_at: update.marked_at }, ...prev].slice(0, 10));
        setToast(`${update.name} marked present`);
        setToastKey((key) => key + 1);
      },
      onActivity: (event: ActivityUpdateEvent) => {
        if (!active) return;
        setActivityLog((prev) =>
          [{ activity_type: event.activity_type, student: event.student, created_at: event.created_at }, ...prev].slice(0, 20)
        );
      },
      onStatusChange: (status) => {
        if (active) setWsStatus(status);
      },
    });

    return () => {
      active = false;
      handle.close();
    };
  }, [sessionId]);

  const handleStop = async () => {
    if (!sessionId) return;
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
          <p className="mt-3 text-muted">QR refreshes every 15 seconds</p>
        </Col>
        <Col md={6}>
          <div className="d-flex align-items-center gap-2 mb-3">
            <span className="text-muted">Present:</span>
            <span className="stamp stamp-present">{presentCount}</span>
            {wsStatus !== "connected" && (
              <span className="stamp stamp-neutral">{wsStatus === "reconnecting" ? "Reconnecting" : "Disconnected"}</span>
            )}
          </div>
          <ListGroup>
            {recent.map((record) => (
              <ListGroup.Item key={record.crn}>
                {record.name} <span className="text-muted font-mono">({record.crn})</span>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Col>
      </Row>
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
      <div className="text-center mt-4">
        <Button variant="danger" onClick={handleStop}>
          Stop Attendance
        </Button>
      </div>
      <ToastContainer position="top-end" className="p-3">
        <Toast key={toastKey} show={!!toast} onClose={() => setToast(null)} delay={3000} autohide bg="success">
          <Toast.Body className="text-white d-flex align-items-center gap-2">
            <span className="stamp stamp-animated" style={{ borderColor: "#fff", color: "#fff" }}>
              Present
            </span>
            {toast}
          </Toast.Body>
        </Toast>
      </ToastContainer>
    </AppShell>
  );
}
