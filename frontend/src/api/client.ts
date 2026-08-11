import axios from "axios";

const BASE_URL = "http://localhost:8000/api";

export const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("classpulse_token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  first_name: string;
  crn: string;
  course: string;
  semester: number;
  section: string;
}

export interface LoginResponse {
  token: string;
  role: "student" | "teacher";
  username: string;
}

export async function registerStudent(payload: RegisterPayload) {
  const { data } = await api.post("/student/register/", payload);
  return data;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/student/login/", { username, password });
  localStorage.setItem("classpulse_token", data.token);
  localStorage.setItem("classpulse_role", data.role);
  return data;
}

export async function getStudentProfile() {
  const { data } = await api.get("/student/profile/");
  return data;
}

export async function getTeacherProfile() {
  const { data } = await api.get("/teacher/profile/");
  return data;
}

export function logout() {
  localStorage.removeItem("classpulse_token");
  localStorage.removeItem("classpulse_role");
}

export interface SessionResponse {
  id: number;
  subject: string;
  date: string;
  start_time: string;
  end_time?: string | null;
  status: "active" | "closed";
}

export interface QRTokenResponse {
  token: string;
  expires_at: string;
}

export async function startSession(subject: string): Promise<SessionResponse> {
  const { data } = await api.post<SessionResponse>("/attendance/sessions/start/", { subject });
  return data;
}

export async function stopSession(sessionId: number): Promise<SessionResponse> {
  const { data } = await api.post<SessionResponse>(`/attendance/sessions/${sessionId}/stop/`);
  return data;
}

export async function getSessionQR(sessionId: number): Promise<QRTokenResponse> {
  const { data } = await api.get<QRTokenResponse>(`/attendance/sessions/${sessionId}/qr/`);
  return data;
}

export async function markAttendance(token: string) {
  const { data } = await api.post("/attendance/mark/", { token });
  return data;
}

export interface AttendanceRecord {
  name: string;
  crn: string;
  marked_at: string;
}

export interface LiveSessionResponse {
  present_count: number;
  recent: AttendanceRecord[];
}

export async function getSessionLive(sessionId: number): Promise<LiveSessionResponse> {
  const { data } = await api.get<LiveSessionResponse>(`/attendance/sessions/${sessionId}/live/`);
  return data;
}
