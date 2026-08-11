import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Container, Button, Spinner, Alert, Badge, ListGroup, Toast, ToastContainer, Row, Col } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, getSessionLive, stopSession } from "../../api/client";
import type { AttendanceRecord } from "../../api/client";
import { connectToAttendanceSocket } from "../../api/ws";
import type { AttendanceUpdateEvent } from "../../api/ws";

const QR_REFRESH_MS = 15000;

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [presentCount, setPresentCount] = useState(0);
  const [recent, setRecent] = useState<AttendanceRecord[]>([]);
  const [toast, setToast] = useState<string | null>(null);

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

    getSessionLive(id).then((data) => {
      if (active) {
        setPresentCount(data.present_count);
        setRecent(data.recent);
      }
    });

    const socket = connectToAttendanceSocket(id, (update: AttendanceUpdateEvent) => {
      if (!active) return;
      setPresentCount(update.present_count);
      setRecent((prev) => [{ name: update.name, crn: update.crn, marked_at: update.marked_at }, ...prev].slice(0, 10));
      setToast(`${update.name} marked present`);
    });

    return () => {
      active = false;
      socket.close();
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
            Present: <Badge bg="success">{presentCount}</Badge>
          </h4>
          <ListGroup className="mt-3">
            {recent.map((record, index) => (
              <ListGroup.Item key={`${record.crn}-${index}`}>
                {record.name} <span className="text-muted">({record.crn})</span>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Col>
      </Row>
      <div className="text-center mt-4">
        <Button variant="danger" onClick={handleStop}>
          Stop Attendance
        </Button>
      </div>
      <ToastContainer position="top-end" className="p-3">
        <Toast show={!!toast} onClose={() => setToast(null)} delay={3000} autohide bg="success">
          <Toast.Body className="text-white">{toast}</Toast.Body>
        </Toast>
      </ToastContainer>
    </Container>
  );
}
