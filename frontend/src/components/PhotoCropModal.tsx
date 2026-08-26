import { useEffect, useRef, useState } from "react";
import { Modal, Button, Form } from "react-bootstrap";

const VIEWPORT_SIZE = 280;
const OUTPUT_SIZE = 512;
const MIN_ZOOM = 1;
const MAX_ZOOM = 3;

interface PhotoCropModalProps {
  show: boolean;
  imageSrc: string | null;
  fileName: string;
  onCancel: () => void;
  onConfirm: (file: File) => void;
  confirming: boolean;
}

// Crops any image down to a 1:1 square via drag-to-pan + zoom, so the backend's
// square-image requirement is met by construction instead of trial and error.
export default function PhotoCropModal({ show, imageSrc, fileName, onCancel, onConfirm, confirming }: PhotoCropModalProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [zoom, setZoom] = useState(MIN_ZOOM);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragState = useRef<{ startX: number; startY: number; offsetX: number; offsetY: number } | null>(null);

  useEffect(() => {
    if (!show) {
      setZoom(MIN_ZOOM);
      setOffset({ x: 0, y: 0 });
      setNaturalSize({ width: 0, height: 0 });
    }
  }, [show]);

  const baseScale = naturalSize.width > 0 ? VIEWPORT_SIZE / Math.min(naturalSize.width, naturalSize.height) : 1;
  const displayScale = baseScale * zoom;
  const displayWidth = naturalSize.width * displayScale;
  const displayHeight = naturalSize.height * displayScale;

  const clampOffset = (x: number, y: number, width: number, height: number) => ({
    x: Math.min(0, Math.max(VIEWPORT_SIZE - width, x)),
    y: Math.min(0, Math.max(VIEWPORT_SIZE - height, y)),
  });

  const handleImageLoad = () => {
    const img = imgRef.current;
    if (!img) return;
    const width = img.naturalWidth;
    const height = img.naturalHeight;
    setNaturalSize({ width, height });
    const scale = VIEWPORT_SIZE / Math.min(width, height);
    setOffset({ x: (VIEWPORT_SIZE - width * scale) / 2, y: (VIEWPORT_SIZE - height * scale) / 2 });
  };

  const handleZoomChange = (nextZoom: number) => {
    const nextScale = baseScale * nextZoom;
    const nextWidth = naturalSize.width * nextScale;
    const nextHeight = naturalSize.height * nextScale;
    setZoom(nextZoom);
    setOffset((prev) => clampOffset(prev.x, prev.y, nextWidth, nextHeight));
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    dragState.current = { startX: e.clientX, startY: e.clientY, offsetX: offset.x, offsetY: offset.y };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragState.current) return;
    const dx = e.clientX - dragState.current.startX;
    const dy = e.clientY - dragState.current.startY;
    setOffset(clampOffset(dragState.current.offsetX + dx, dragState.current.offsetY + dy, displayWidth, displayHeight));
  };

  const handlePointerUp = () => {
    dragState.current = null;
  };

  const handleConfirm = () => {
    const img = imgRef.current;
    if (!img || naturalSize.width === 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = OUTPUT_SIZE;
    canvas.height = OUTPUT_SIZE;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const sx = -offset.x / displayScale;
    const sy = -offset.y / displayScale;
    const sSize = VIEWPORT_SIZE / displayScale;
    ctx.drawImage(img, sx, sy, sSize, sSize, 0, 0, OUTPUT_SIZE, OUTPUT_SIZE);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const croppedName = fileName.replace(/\.[^.]+$/, "") + ".jpg";
        onConfirm(new File([blob], croppedName, { type: "image/jpeg" }));
      },
      "image/jpeg",
      0.92
    );
  };

  return (
    <Modal show={show} onHide={onCancel} centered>
      <Modal.Header closeButton>
        <Modal.Title className="h5">Crop photo</Modal.Title>
      </Modal.Header>
      <Modal.Body className="text-center">
        <div
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          style={{
            width: VIEWPORT_SIZE,
            height: VIEWPORT_SIZE,
            margin: "0 auto",
            overflow: "hidden",
            position: "relative",
            border: "2px solid var(--line)",
            borderRadius: 8,
            background: "#00000010",
            cursor: "grab",
            touchAction: "none",
          }}
        >
          {imageSrc && (
            <img
              ref={imgRef}
              src={imageSrc}
              alt="Crop preview"
              onLoad={handleImageLoad}
              draggable={false}
              style={{
                position: "absolute",
                left: offset.x,
                top: offset.y,
                width: displayWidth || undefined,
                height: displayHeight || undefined,
                maxWidth: "none",
                userSelect: "none",
              }}
            />
          )}
        </div>
        <div className="mt-3">
          <Form.Label className="small text-muted">Zoom</Form.Label>
          <Form.Range
            min={MIN_ZOOM}
            max={MAX_ZOOM}
            step={0.01}
            value={zoom}
            onChange={(e) => handleZoomChange(Number(e.target.value))}
          />
        </div>
        <div className="text-muted small">Drag to reposition, use the slider to zoom.</div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={onCancel} disabled={confirming}>
          Cancel
        </Button>
        <Button onClick={handleConfirm} disabled={confirming || !imageSrc}>
          {confirming ? "Uploading..." : "Crop & Upload"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
