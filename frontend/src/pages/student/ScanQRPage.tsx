import { useEffect, useRef, useState } from "react";
import { Container, Alert } from "react-bootstrap";
import { Html5Qrcode, Html5QrcodeScannerState } from "html5-qrcode";
import { markAttendance } from "../../api/client";

const SCANNER_ELEMENT_ID = "qr-scanner";

export default function ScanQRPage() {
  const [message, setMessage] = useState<{ type: "success" | "danger"; text: string } | null>(null);
  const scanningRef = useRef(false);

  useEffect(() => {
    const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID);
    let active = true;
    let debounceTimeout: ReturnType<typeof setTimeout> | undefined;

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 250 },
        async (decodedText) => {
          if (scanningRef.current) return;
          scanningRef.current = true;
          try {
            await markAttendance(decodedText);
            if (active) setMessage({ type: "success", text: "Attendance marked!" });
          } catch (err: any) {
            const data = err?.response?.data;
            const detail = data?.token?.[0] || data?.non_field_errors?.[0] || "Could not mark attendance.";
            if (active) setMessage({ type: "danger", text: detail });
          } finally {
            debounceTimeout = setTimeout(() => {
              scanningRef.current = false;
            }, 2000);
          }
        },
        () => {}
      )
      .catch(() => {
        if (active) setMessage({ type: "danger", text: "Could not access camera." });
      });

    return () => {
      active = false;
      if (debounceTimeout) clearTimeout(debounceTimeout);
      if (scanner.getState() === Html5QrcodeScannerState.SCANNING) {
        scanner.stop().catch(() => {});
      }
    };
  }, []);

  return (
    <Container className="py-4">
      <h2>Scan Attendance QR</h2>
      {message && <Alert variant={message.type}>{message.text}</Alert>}
      <div id={SCANNER_ELEMENT_ID} style={{ width: "100%", maxWidth: 400 }} />
    </Container>
  );
}
