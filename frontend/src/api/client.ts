import axios from "axios";

const BASE_URL = "http://localhost:8000/api";

// Matches the backend's attendance_percentage() convention (see attendance/views.py's
// AnalyticsView.below_threshold) — kept in one place so the frontend badge coloring and
// the backend's below-threshold list can't silently drift apart.
export const ATTENDANCE_THRESHOLD = 75;

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
  duration_minutes: number;
  periods: number;
  closes_at: string;
  status: "active" | "closed";
}

export interface QRTokenResponse {
  token: string;
  expires_at: string;
}

export interface CurrentScheduleResponse {
  matched: boolean;
  subject?: string;
  section?: string;
  start_time?: string;
  end_time?: string;
}

export async function getCurrentSchedule(): Promise<CurrentScheduleResponse> {
  const { data } = await api.get<CurrentScheduleResponse>("/attendance/schedule/current/");
  return data;
}

export interface ScheduleSlot {
  subject: string;
  section: string;
  start_time: string;
  end_time: string;
  periods: number;
  session_id: number | null;
  session_status: "active" | "closed" | null;
}

export interface TodayScheduleResponse {
  day: string;
  slots: ScheduleSlot[];
}

export async function getTodaySchedule(): Promise<TodayScheduleResponse> {
  const { data } = await api.get<TodayScheduleResponse>("/attendance/schedule/today/");
  return data;
}

export async function startSession(
  subject: string,
  durationMinutes: number,
  periods: number = 1,
  section: string = ""
): Promise<SessionResponse> {
  const { data } = await api.post<SessionResponse>("/attendance/sessions/start/", {
    subject,
    duration_minutes: durationMinutes,
    periods,
    section,
  });
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
  status: "active" | "closed";
  closes_at: string;
  section: string;
}

export async function getSessionLive(sessionId: number): Promise<LiveSessionResponse> {
  const { data } = await api.get<LiveSessionResponse>(`/attendance/sessions/${sessionId}/live/`);
  return data;
}

export interface ActivityLogEntry {
  activity_type: "duplicate" | "expired_token" | "invalid_token" | "session_closed" | "new_device" | "wrong_section";
  student: string;
  created_at: string;
}

export interface ActivityLogResponse {
  logs: ActivityLogEntry[];
}

export async function getSessionActivity(sessionId: number): Promise<ActivityLogResponse> {
  const { data } = await api.get<ActivityLogResponse>(`/attendance/sessions/${sessionId}/activity/`);
  return data;
}

export interface AttendanceHistoryEntry {
  date: string;
  subject: string;
  status: "present" | "absent";
}

export interface AttendanceHistoryResponse {
  total: number;
  present: number;
  percentage: number;
  history: AttendanceHistoryEntry[];
}

export async function getStudentHistory(): Promise<AttendanceHistoryResponse> {
  const { data } = await api.get<AttendanceHistoryResponse>("/attendance/student/history/");
  return data;
}

export interface StudentAnalyticsRow {
  name: string;
  crn: string;
  roll_number: string;
  present: number;
  total: number;
  percentage: number;
}

export interface AnalyticsResponse {
  total_sessions: number;
  total_students: number;
  overall_rate: number;
  students: StudentAnalyticsRow[];
  below_threshold: StudentAnalyticsRow[];
  available_sections: string[];
  section: string;
}

export async function getAnalytics(section?: string): Promise<AnalyticsResponse> {
  const { data } = await api.get<AnalyticsResponse>("/attendance/analytics/", {
    params: section ? { section } : undefined,
  });
  return data;
}

export interface DayAttendanceSession {
  id: number;
  start_time: string;
  periods: number;
  status: "active" | "closed";
}

export interface DayAttendanceStudent {
  crn: string;
  roll_number: string;
  name: string;
  present: boolean;
}

export interface DayAttendanceResponse {
  date: string;
  section: string;
  sessions: DayAttendanceSession[];
  present_count: number;
  total_students: number;
  students: DayAttendanceStudent[];
}

export async function getDayAttendance(section: string, date: string): Promise<DayAttendanceResponse> {
  const { data } = await api.get<DayAttendanceResponse>("/attendance/day/", {
    params: { section, date },
  });
  return data;
}

export async function setManualAttendance(sessionId: number, crn: string, present: boolean): Promise<void> {
  await api.post(`/attendance/sessions/${sessionId}/manual/`, { crn, present });
}

export async function downloadReport(format: "csv" | "excel" | "pdf", section?: string): Promise<void> {
  const response = await api.get(`/attendance/export/${format}/`, {
    responseType: "blob",
    params: section ? { section } : undefined,
  });
  const extension = format === "excel" ? "xlsx" : format;
  const blob = new Blob([response.data]);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `attendance_report.${extension}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoking synchronously can abort the download handoff in Safari/WebKit, where it's
  // asynchronous; a short delay costs nothing and removes the cross-browser risk.
  setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}
