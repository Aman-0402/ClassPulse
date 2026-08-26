import { useEffect, useState } from "react";
import { Toast, ToastContainer, Button } from "react-bootstrap";

const SHOWN_FLAG = "classpulse_install_prompt_shown";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function isMobile(): boolean {
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

function isStandalone(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

function isIos(): boolean {
  return /iPhone|iPad|iPod/i.test(navigator.userAgent);
}

// One-time "install this as an app" nudge for students on mobile. Android/Chrome
// gets the real native install flow via beforeinstallprompt; iOS Safari has no such
// API at all, so it gets a one-time instructional banner instead ("Share > Add to
// Home Screen") — the closest thing to an install prompt that platform allows.
export default function InstallPrompt() {
  const [deferredEvent, setDeferredEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [showIosBanner, setShowIosBanner] = useState(false);

  useEffect(() => {
    const role = localStorage.getItem("classpulse_role");
    if (role !== "student") return;
    if (!isMobile() || isStandalone()) return;
    if (localStorage.getItem(SHOWN_FLAG)) return;

    if (isIos()) {
      setShowIosBanner(true);
      localStorage.setItem(SHOWN_FLAG, "1");
      return;
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredEvent(e as BeforeInstallPromptEvent);
      localStorage.setItem(SHOWN_FLAG, "1");
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredEvent) return;
    await deferredEvent.prompt();
    await deferredEvent.userChoice;
    setDeferredEvent(null);
  };

  if (!deferredEvent && !showIosBanner) return null;

  return (
    <ToastContainer position="bottom-center" className="p-3">
      <Toast onClose={() => { setDeferredEvent(null); setShowIosBanner(false); }} bg="dark">
        <Toast.Body className="text-white">
          {deferredEvent ? (
            <div className="d-flex align-items-center justify-content-between gap-3">
              <span>Install ClassPulse on your phone for quick access.</span>
              <div className="d-flex gap-2 flex-shrink-0">
                <Button size="sm" variant="light" onClick={handleInstall}>
                  Install
                </Button>
                <Button size="sm" variant="outline-light" onClick={() => setDeferredEvent(null)}>
                  Not now
                </Button>
              </div>
            </div>
          ) : (
            <div className="d-flex align-items-center justify-content-between gap-3">
              <span>Add ClassPulse to your Home Screen: tap Share, then "Add to Home Screen".</span>
              <Button size="sm" variant="outline-light" onClick={() => setShowIosBanner(false)}>
                Got it
              </Button>
            </div>
          )}
        </Toast.Body>
      </Toast>
    </ToastContainer>
  );
}
