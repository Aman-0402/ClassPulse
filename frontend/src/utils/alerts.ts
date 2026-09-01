import Swal from "sweetalert2";

// Shared SweetAlert2 styling so every popup in the app looks consistent —
// this is the second call site to need the exact same confirmButtonColor
// (ScanQRPage was the first), worth a shared helper instead of repeating it.
const CONFIRM_COLOR = "#9d5fd1";

export function notifySuccess(title: string, text?: string) {
  return Swal.fire({ icon: "success", title, text, confirmButtonColor: CONFIRM_COLOR });
}

export function notifyError(title: string, text?: string) {
  return Swal.fire({ icon: "error", title, text, confirmButtonColor: CONFIRM_COLOR });
}

export function notifyInfo(title: string, text?: string) {
  return Swal.fire({ icon: "info", title, text, confirmButtonColor: CONFIRM_COLOR });
}
