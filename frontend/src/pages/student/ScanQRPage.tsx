import { useEffect, useRef } from "react";
import { Html5Qrcode, Html5QrcodeScannerState } from "html5-qrcode";
import { markAttendance } from "../../api/client";
import AppShell from "../../components/AppShell";
import { notifySuccess, notifyError, notifyInfo } from "../../utils/alerts";

const SCANNER_ELEMENT_ID = "qr-scanner";
const DUPLICATE_MESSAGE = "Attendance already marked for this session.";
const RESCAN_COOLDOWN_MS = 2000;

export default function ScanQRPage() {
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
            if (active) {
              notifySuccess("Attendance Marked!", "You have marked your attendance.");
            }
          } catch (err: any) {
            if (!active) return;
            // The backend reports every rejection (duplicate, expired QR, wrong
            // section, invalid token) as {"detail": "..."} — a DRF validation
            // error on the token field itself (rare, malformed payload) instead
            // uses {"token": [...]}.
            const data = err?.response?.data;
            const detail: string = data?.detail || data?.token?.[0] || "Could not mark attendance.";

            if (detail === DUPLICATE_MESSAGE) {
              notifyInfo("Already Marked", "You have already marked your attendance for this session.");
            } else {
              notifyError("Scan Failed", `${detail} Please try scanning again in a few seconds.`);
            }
          } finally {
            debounceTimeout = setTimeout(() => {
              scanningRef.current = false;
            }, RESCAN_COOLDOWN_MS);
          }
        },
        () => {}
      )
      .catch(() => {
        if (active) {
          notifyError("Camera Unavailable", "Could not access the camera. Please allow camera access and try again.");
        }
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
    <AppShell>
      <h1 className="h3 mb-3">Scan Attendance QR</h1>
      <div
        id={SCANNER_ELEMENT_ID}
        style={{ width: "100%", maxWidth: 400, borderRadius: "0.75rem", overflow: "hidden" }}
      />
    </AppShell>
  );
}
