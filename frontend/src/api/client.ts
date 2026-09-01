import axios from "axios";

// Auto-switches so `npm run dev` always talks to a local backend and a real
// build (`npm run build`, what actually gets deployed) always talks to
// production — no more manually editing this before every deploy and
// forgetting to revert it for local dev.
const BASE_URL = import.meta.env.DEV ? "http://localhost:8000/api" : "https://arxinfo.info/api";

// Django admin lives alongside the API under the same mount — used to deep-link
// a teacher straight to reviewing pending profile-edit requests.
export const ADMIN_URL = `${BASE_URL}/admin/`;

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

export interface LoginResponse {
  token: string;
  role: "student" | "teacher";
  username: string;
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

export interface ProfileEditRequestPayload {
  requested_name?: string;
  requested_crn?: string;
  requested_urn?: string;
  reason?: string;
}

export interface ProfileEditRequestRecord {
  id: number;
  requested_name: string;
  requested_crn: string;
  requested_urn: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  reviewed_at: string | null;
}

export async function submitProfileEditRequest(
  payload: ProfileEditRequestPayload
): Promise<ProfileEditRequestRecord> {
  const { data } = await api.post<ProfileEditRequestRecord>("/student/edit-request/", payload);
  return data;
}

export async function getMyEditRequests(): Promise<ProfileEditRequestRecord[]> {
  const { data } = await api.get<ProfileEditRequestRecord[]>("/student/edit-request/");
  return data;
}

export async function uploadProfilePhoto(file: File): Promise<{ photo: string | null }> {
  const formData = new FormData();
  formData.append("photo", file);
  const { data } = await api.post("/student/photo/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getTeacherProfile() {
  const { data } = await api.get("/teacher/profile/");
  return data;
}

export function logout() {
  // Best-effort — revoke the token server-side before clearing it locally, so it
  // can't be replayed after "logout" (previously this only cleared localStorage,
  // leaving the token valid forever). Fire-and-forget: every caller in this app
  // treats logout() as synchronous and navigates immediately after, so this must
  // not block on the network or on the request failing (e.g. already offline).
  api.post("/logout/").catch(() => {});
  localStorage.removeItem("classpulse_token");
  localStorage.removeItem("classpulse_role");
}

export interface ChangePasswordResponse {
  token: string;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const { data } = await api.post<ChangePasswordResponse>("/change-password/", {
    old_password: oldPassword,
    new_password: newPassword,
  });
  localStorage.setItem("classpulse_token", data.token);
}

// The OTP itself is never sent to the student by this call — it's generated
// server-side and only visible to the admin (teacher's OTP History page, or
// Django admin), who relays it to the student out-of-band (in person/phone
// call). No SMS/email service exists for this app, so this is deliberately
// not a "you'll receive a code" flow.
export async function requestPasswordResetOtp(username: string): Promise<void> {
  await api.post("/forgot-password/", { username });
}

export async function resetPasswordWithOtp(username: string, otp: string, newPassword: string): Promise<void> {
  await api.post("/reset-password/", { username, otp, new_password: newPassword });
}

export interface OTPHistoryEntry {
  id: number;
  username: string;
  full_name: string;
  code: string;
  created_at: string;
  expires_at: string;
  used_at: string | null;
  status: "active" | "used" | "expired";
}

export async function getOtpHistory(): Promise<OTPHistoryEntry[]> {
  const { data } = await api.get<OTPHistoryEntry[]>("/teacher/otp-history/");
  return data;
}

export async function updateEmail(email: string) {
  const { data } = await api.post("/student/email/", { email });
  return data;
}

export async function updateContactNumber(contactNumber: string) {
  const { data } = await api.post("/student/contact-number/", { contact_number: contactNumber });
  return data;
}

export async function updateTeacherEmail(email: string) {
  const { data } = await api.post("/teacher/email/", { email });
  return data;
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

export async function resumeSession(sessionId: number): Promise<SessionResponse> {
  const { data } = await api.post<SessionResponse>(`/attendance/sessions/${sessionId}/resume/`);
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
  photo: string | null;
  marked_at: string;
}

export interface LiveSessionResponse {
  present_count: number;
  recent: AttendanceRecord[];
  status: "active" | "closed";
  closes_at: string;
  section: string;
  roster: DayAttendanceStudent[];
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
  date_from: string | null;
  date_to: string | null;
}

export async function getAnalytics(
  section?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<AnalyticsResponse> {
  const { data } = await api.get<AnalyticsResponse>("/attendance/analytics/", {
    params: {
      ...(section ? { section } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    },
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
  // Only populated on the live-session roster (SessionLiveView) — the
  // per-day attendance view has no single "the" session to time-stamp against.
  marked_at?: string | null;
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

export async function downloadReport(
  format: "csv" | "excel" | "pdf",
  section?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<void> {
  const response = await api.get(`/attendance/export/${format}/`, {
    responseType: "blob",
    params: {
      ...(section ? { section } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    },
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
