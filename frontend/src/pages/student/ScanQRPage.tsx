import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Card } from "react-bootstrap";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Html5Qrcode, Html5QrcodeScannerState } from "html5-qrcode";
import { markAttendance } from "../../api/client";
import AppShell from "../../components/AppShell";
import Swal from "sweetalert2";
import { notifySuccess, notifyError, notifyInfo } from "../../utils/alerts";

const SCANNER_ELEMENT_ID = "qr-scanner";
const DUPLICATE_MESSAGE = "Attendance already marked for this session.";
const RESCAN_COOLDOWN_MS = 2000;

type ScanStatus = {
  variant: "info" | "success" | "danger" | "warning";
  title: string;
  message: string;
};

function tokenFromScan(decodedText: string): string {
  try {
    const url = new URL(decodedText);
    return url.searchParams.get("token") || decodedText;
  } catch {
    return decodedText;
  }
}

export default function ScanQRPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [cameraStarted, setCameraStarted] = useState(false);
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const scanningRef = useRef(false);
  const urlTokenRef = useRef(searchParams.get("token"));
  const urlToken = urlTokenRef.current;

  const submitToken = useCallback(async (token: string, active: () => boolean, showScreenStatus = false) => {
    if (scanningRef.current) return;
    scanningRef.current = true;
    if (showScreenStatus) {
      setStatus({
        variant: "info",
        title: "Marking Attendance",
        message: "Please wait while ClassPulse verifies this QR.",
      });
    }
    try {
      await markAttendance(token);
      if (active()) {
        if (showScreenStatus) {
          setStatus({
            variant: "success",
            title: "Attendance Marked",
            message: "Your attendance has been marked successfully.",
          });
        }
        notifySuccess("Attendance Marked!", "You have marked your attendance.");
      }
    } catch (err: any) {
      if (!active()) return;
      // The backend reports every rejection (duplicate, expired QR, wrong
      // section, invalid token) as {"detail": "..."} — a DRF validation
      // error on the token field itself (rare, malformed payload) instead
      // uses {"token": [...]}.
      const data = err?.response?.data;
      const detail: string = data?.detail || data?.token?.[0] || "Could not mark attendance.";

      if (detail === DUPLICATE_MESSAGE) {
        if (showScreenStatus) {
          setStatus({
            variant: "warning",
            title: "Already Marked",
            message: "Your attendance was already marked for this session.",
          });
        }
        notifyInfo("Already Marked", "You have already marked your attendance for this session.");
      } else if (data?.code === "incomplete_profile") {
        // The message already names exactly what's still missing; the button
        // takes them to the profile page where those fields are marked red.
        if (showScreenStatus) {
          setStatus({ variant: "danger", title: "Complete Your Profile", message: detail });
        }
        Swal.fire({
          icon: "warning",
          title: "Complete Your Profile",
          text: detail,
          confirmButtonText: "Complete profile",
          confirmButtonColor: "#9d5fd1",
          showCancelButton: true,
          cancelButtonText: "Later",
        }).then((result) => {
          if (result.isConfirmed) navigate("/student/profile", { state: { fromScan: true } });
        });
      } else {
        if (showScreenStatus) {
          setStatus({
            variant: "danger",
            title: "Attendance Not Marked",
            message: detail,
          });
        }
        notifyError("Scan Failed", `${detail} Please try scanning again in a few seconds.`);
      }
    } finally {
      setTimeout(() => {
        scanningRef.current = false;
      }, RESCAN_COOLDOWN_MS);
    }
  }, [navigate]);

  useEffect(() => {
    if (!urlToken) return;
    let active = true;
    navigate("/student/scan", { replace: true });
    submitToken(urlToken, () => active, true);
    return () => {
      active = false;
    };
  }, [navigate, submitToken, urlToken]);

  useEffect(() => {
    if (urlToken || !cameraStarted) return;
    const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID);
    let active = true;

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 250 },
        async (decodedText) => {
          await submitToken(tokenFromScan(decodedText), () => active);
        },
        () => {}
      )
      .catch(() => {
        if (active) {
          setStatus({
            variant: "danger",
            title: "Camera Unavailable",
            message: "Allow camera access in your browser settings, then try again.",
          });
          notifyError("Camera Unavailable", "Could not access the camera. Please allow camera access and try again.");
          setCameraStarted(false);
        }
      });

    return () => {
      active = false;
      if (scanner.getState() === Html5QrcodeScannerState.SCANNING) {
        scanner.stop().catch(() => {});
      }
    };
  }, [cameraStarted, submitToken, urlToken]);

  return (
    <AppShell>
      <h1 className="h3 mb-3">Scan Attendance QR</h1>
      {urlToken ? (
        <Alert variant={status?.variant ?? "info"}>
          <Alert.Heading className="h5">{status?.title ?? "Marking Attendance"}</Alert.Heading>
          <p className="mb-0">{status?.message ?? "Please wait while ClassPulse verifies this QR."}</p>
        </Alert>
      ) : !cameraStarted ? (
        <>
          {status && (
            <Alert variant={status.variant}>
              <Alert.Heading className="h5">{status.title}</Alert.Heading>
              <p className="mb-0">{status.message}</p>
            </Alert>
          )}
          <Card style={{ maxWidth: 460 }}>
            <Card.Body>
              <p className="text-muted">
                ClassPulse needs camera access to scan the attendance QR. Choose Allow when your browser asks.
              </p>
              <Button onClick={() => setCameraStarted(true)}>Start Camera</Button>
            </Card.Body>
          </Card>
        </>
      ) : (
        <div
          id={SCANNER_ELEMENT_ID}
          style={{ width: "100%", maxWidth: 400, borderRadius: "0.75rem", overflow: "hidden" }}
        />
      )}
    </AppShell>
  );
}
