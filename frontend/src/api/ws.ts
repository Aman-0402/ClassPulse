const WS_BASE_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY_MS = 3000;

export interface AttendanceUpdateEvent {
  kind: "attendance";
  name: string;
  crn: string;
  photo: string | null;
  marked_at: string;
  present_count: number;
}

export interface ActivityUpdateEvent {
  kind: "activity";
  activity_type: "duplicate" | "expired_token" | "invalid_token" | "session_closed" | "new_device" | "wrong_section";
  student: string;
  created_at: string;
}

export interface AttendanceSocketHandlers {
  onUpdate: (event: AttendanceUpdateEvent) => void;
  onActivity?: (event: ActivityUpdateEvent) => void;
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
        const data = JSON.parse(message.data) as AttendanceUpdateEvent | ActivityUpdateEvent;
        if (data.kind === "activity") {
          handlers.onActivity?.(data);
        } else {
          handlers.onUpdate(data);
        }
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
