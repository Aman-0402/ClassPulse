import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Container, Button, Spinner } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, stopSession } from "../../api/client";

const QR_REFRESH_MS = 15000;

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    const fetchToken = () => {
      getSessionQR(id).then((data) => setToken(data.token));
    };
    fetchToken();
    const interval = setInterval(fetchToken, QR_REFRESH_MS);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleStop = async () => {
    if (!sessionId) return;
    await stopSession(Number(sessionId));
    navigate("/teacher/profile");
  };

  return (
    <Container className="py-4 text-center">
      <h2>Attendance Live</h2>
      {token ? <QRCodeSVG value={token} size={256} /> : <Spinner animation="border" />}
      <p className="mt-3 text-muted">QR refreshes every 15 seconds</p>
      <Button variant="danger" onClick={handleStop}>
        Stop Attendance
      </Button>
    </Container>
  );
}
