import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Container, Button, Spinner, Alert, Badge, ListGroup, Toast, ToastContainer, Row, Col } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, getSessionLive, stopSession, getSessionActivity } from "../../api/client";
import type { AttendanceRecord, ActivityLogEntry } from "../../api/client";
import { connectToAttendanceSocket } from "../../api/ws";
import type { AttendanceUpdateEvent, ActivityUpdateEvent } from "../../api/ws";

const QR_REFRESH_MS = 15000;

const ACTIVITY_LABELS: Record<ActivityLogEntry["activity_type"], { label: string; variant: string }> = {
  duplicate: { label: "Duplicate scan", variant: "warning" },
  expired_token: { label: "Expired QR", variant: "danger" },
  invalid_token: { label: "Invalid QR", variant: "danger" },
  session_closed: { label: "Closed-session attempt", variant: "secondary" },
  new_device: { label: "New device", variant: "info" },
};

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [presentCount, setPresentCount] = useState(0);
  const [recent, setRecent] = useState<AttendanceRecord[]>([]);
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);
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
        if (active) setActivityLog(data.logs);
      })
      .catch(() => {
        // Non-critical panel — a failed initial fetch just leaves it empty; the live WS feed will still populate it going forward.
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
    <Container className="py-4">
      <h2 className="text-center">Attendance Live</h2>
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
          <h4>
            Present: <Badge bg="success">{presentCount}</Badge>{" "}
            {wsStatus !== "connected" && (
              <Badge bg="warning" className="ms-2">
                {wsStatus === "reconnecting" ? "Reconnecting..." : "Disconnected"}
              </Badge>
            )}
          </h4>
          <ListGroup className="mt-3">
            {recent.map((record) => (
              <ListGroup.Item key={record.crn}>
                {record.name} <span className="text-muted">({record.crn})</span>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Col>
      </Row>
      {activityLog.length > 0 && (
        <div className="mt-4">
          <h5>Suspicious Activity</h5>
          <ListGroup>
            {activityLog.map((entry, index) => {
              const meta = ACTIVITY_LABELS[entry.activity_type];
              return (
                <ListGroup.Item key={`${entry.student}-${entry.created_at}-${index}`}>
                  <Badge bg={meta.variant} className="me-2">
                    {meta.label}
                  </Badge>
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
          <Toast.Body className="text-white">{toast}</Toast.Body>
        </Toast>
      </ToastContainer>
    </Container>
  );
}
