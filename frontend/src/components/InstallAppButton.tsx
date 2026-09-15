import { useEffect, useState } from "react";
import { Button, Modal } from "react-bootstrap";
import { notifyInfo } from "../utils/alerts";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
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

function isAndroid(): boolean {
  return /Android/i.test(navigator.userAgent);
}

export default function InstallAppButton() {
  const [deferredEvent, setDeferredEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(() => isStandalone());
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    const handler = (event: Event) => {
      event.preventDefault();
      setDeferredEvent(event as BeforeInstallPromptEvent);
    };
    const installedHandler = () => setInstalled(true);

    window.addEventListener("beforeinstallprompt", handler);
    window.addEventListener("appinstalled", installedHandler);
    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("appinstalled", installedHandler);
    };
  }, []);

  const handleInstall = async () => {
    if (installed) {
      notifyInfo("Already Installed", "ClassPulse is already installed on this device.");
      return;
    }

    if (deferredEvent) {
      await deferredEvent.prompt();
      const choice = await deferredEvent.userChoice;
      if (choice.outcome === "accepted") {
        setInstalled(true);
      }
      setDeferredEvent(null);
      return;
    }

    if (isIos()) {
      setShowHelp(true);
      return;
    }

    setShowHelp(true);
  };

  return (
    <>
      <Button variant="outline-secondary" onClick={handleInstall} disabled={installed}>
        {installed ? "App Installed" : "Install App"}
      </Button>

      <Modal show={showHelp} onHide={() => setShowHelp(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title className="h5">Install ClassPulse</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {isIos() ? (
            <>
              <p className="text-muted">
                iPhone does not allow websites to open the install prompt directly.
              </p>
              <ol className="mb-0">
                <li>Open ClassPulse in Safari.</li>
                <li>Tap the Share button.</li>
                <li>Tap Add to Home Screen.</li>
                <li>Tap Add.</li>
              </ol>
            </>
          ) : isAndroid() ? (
            <>
              <p className="text-muted">
                If the install prompt did not open, use your browser menu.
              </p>
              <ol className="mb-0">
                <li>Open ClassPulse in Chrome or Edge.</li>
                <li>Tap the three-dot menu.</li>
                <li>Tap Install app or Add to Home screen.</li>
                <li>Confirm Install.</li>
              </ol>
            </>
          ) : (
            <p className="text-muted mb-0">
              Open ClassPulse in Chrome, Edge, or Safari and use the browser menu to install or add it to your home screen.
            </p>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowHelp(false)}>
            Done
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
