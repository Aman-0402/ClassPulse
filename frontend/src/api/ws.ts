const WS_BASE_URL = "ws://localhost:8000/ws";

export interface AttendanceUpdateEvent {
  name: string;
  crn: string;
  marked_at: string;
  present_count: number;
}

export function connectToAttendanceSocket(
  sessionId: number,
  onUpdate: (event: AttendanceUpdateEvent) => void
): WebSocket {
  const token = localStorage.getItem("classpulse_token");
  const socket = new WebSocket(`${WS_BASE_URL}/attendance/${sessionId}/?token=${token ?? ""}`);

  socket.onmessage = (message) => {
    try {
      const data = JSON.parse(message.data) as AttendanceUpdateEvent;
      onUpdate(data);
    } catch {
      // Ignore malformed messages rather than crashing the socket handler.
    }
  };

  return socket;
}
