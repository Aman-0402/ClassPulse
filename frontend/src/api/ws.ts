const WS_BASE_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY_MS = 3000;

export interface AttendanceUpdateEvent {
  name: string;
  crn: string;
  marked_at: string;
  present_count: number;
}

export interface AttendanceSocketHandlers {
  onUpdate: (event: AttendanceUpdateEvent) => void;
  onStatusChange?: (status: "connected" | "disconnected" | "reconnecting") => void;
}

export interface AttendanceSocketHandle {
  close: () => void;
}

export function connectToAttendanceSocket(
  sessionId: number,
  handlers: AttendanceSocketHandlers
): AttendanceSocketHandle {
  let closedByCaller = false;
  let socket: WebSocket | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | undefined;

  const open = () => {
    const token = localStorage.getItem("classpulse_token");
    socket = new WebSocket(`${WS_BASE_URL}/attendance/${sessionId}/?token=${token ?? ""}`);

    socket.onopen = () => {
      handlers.onStatusChange?.("connected");
    };

    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data) as AttendanceUpdateEvent;
        handlers.onUpdate(data);
      } catch {
        // Ignore malformed messages rather than crashing the socket handler.
      }
    };

    socket.onerror = () => {
      handlers.onStatusChange?.("disconnected");
    };

    socket.onclose = () => {
      if (closedByCaller) return;
      handlers.onStatusChange?.("reconnecting");
      reconnectTimeout = setTimeout(open, RECONNECT_DELAY_MS);
    };
  };

  open();

  return {
    close: () => {
      closedByCaller = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      socket?.close();
    },
  };
}
