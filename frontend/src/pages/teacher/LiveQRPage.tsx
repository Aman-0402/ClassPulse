import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Container, Button, Spinner, Alert } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, stopSession } from "../../api/client";

const QR_REFRESH_MS = 15000;

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    let active = true;
    const fetchToken = () => {
      getSessionQR(id)
        .then((data) => {
          if (active) setToken(data.token);
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
    <Container className="py-4 text-center">
      <h2>Attendance Live</h2>
      {error && (
        <Alert variant="warning" className="mt-3">
          {error}
        </Alert>
      )}
      {!error && (token ? <QRCodeSVG value={token} size={256} /> : <Spinner animation="border" />)}
      <p className="mt-3 text-muted">QR refreshes every 15 seconds</p>
      <Button variant="danger" onClick={handleStop} className="mt-3">
        Stop Attendance
      </Button>
    </Container>
  );
}
