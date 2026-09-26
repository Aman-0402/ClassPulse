import axios from "axios";
import { clearSession, getToken, saveSession, updateSessionToken } from "../utils/session";

// Auto-switches so `npm run dev` always talks to a local backend and a real
// build (`npm run build`, what actually gets deployed) always talks to
// production - no more manually editing this before every deploy and
// forgetting to revert it for local dev.
const isLocalFrontend =
  typeof window !== "undefined" &&
  (["localhost", "127.0.0.1"].includes(window.location.hostname) ||
    /^10\./.test(window.location.hostname) ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(window.location.hostname) ||
    /^192\.168\./.test(window.location.hostname));

function localApiUrl(): string {
  if (typeof window === "undefined") return "http://localhost:8000/api";
  if (["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return "http://localhost:8000/api";
  }
  return `${window.location.protocol}//${window.location.hostname}:8000/api`;
}

const BASE_URL = import.meta.env.VITE_API_URL || (isLocalFrontend ? localApiUrl() : "https://arxinfo.info/api");

// Public site origin encoded into attendance QR codes. Keep this as the real
// production domain even when the teacher opens a local/dev build, otherwise
// phone camera apps will show localhost links that students cannot open.
export const FRONTEND_URL = import.meta.env.VITE_FRONTEND_URL || "https://arxinfo.info";

// Matches the backend's attendance_percentage() convention (see attendance/views.py's
// AnalyticsView.below_threshold) - kept in one place so the frontend badge coloring and
// the backend's below-threshold list can't silently drift apart.
export const ATTENDANCE_THRESHOLD = 75;

export const api = axios.create({ baseURL: BASE_URL });

function getOrCreateDeviceId(): string {
  const storageKey = "classpulse_device_id";
  const existing = localStorage.getItem(storageKey);
  if (existing) return existing;

  const generated =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  localStorage.setItem(storageKey, generated);
  return generated;
}

api.interceptors.request.use((config) => {
  const token = getToken();
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

export async function login(username: string, password: string, remember: boolean): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/student/login/", { username, password });
  saveSession(data.token, data.role, remember);
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

export async function uploadProfilePhoto(file: File): Promise<{ photo: string | null; missing_scan_fields: ("photo" | "email" | "contact_number")[]; scan_lock_enabled: boolean }> {
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
  // Best-effort - revoke the token server-side before clearing it locally, so it
  // can't be replayed after "logout" (previously this only cleared localStorage,
  // leaving the token valid forever). Fire-and-forget: every caller in this app
  // treats logout() as synchronous and navigates immediately after, so this must
  // not block on the network or on the request failing (e.g. already offline).
  api.post("/logout/").catch(() => {});
  clearSession();
}

// Logout for the Log Out button: unlike logout() it waits for the server, because
// students are locked out of logging out for 10 minutes after signing in. Resolves
// to a message when refused (and keeps the session), or null once logged out.
export async function requestLogout(): Promise<string | null> {
  try {
    await api.post("/logout/");
  } catch (err: any) {
    if (err?.response?.data?.code === "logout_locked") {
      return err.response.data.detail as string;
    }
    // Any other failure (already expired token, offline): still let them out locally.
  }
  clearSession();
  return null;
}

export interface ChangePasswordResponse {
  token: string;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const { data } = await api.post<ChangePasswordResponse>("/change-password/", {
    old_password: oldPassword,
    new_password: newPassword,
  });
  updateSessionToken(data.token);
}

// The OTP itself is never sent to the student by this call - it's generated
// server-side and only visible to the admin (teacher's OTP History page, or
// Django admin), who relays it to the student out-of-band (in person/phone
// call). No SMS/email service exists for this app, so this is deliberately
// not a "you'll receive a code" flow.
export async function requestPasswordResetOtp(username: string): Promise<void> {
  await api.post("/student/forgot-password/", { username });
}

export async function resetPasswordWithOtp(username: string, otp: string, newPassword: string): Promise<void> {
  await api.post("/student/reset-password/", { username, otp, new_password: newPassword });
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

export interface EditRequestReviewEntry {
  id: number;
  username: string;
  full_name: string;
  section: string;
  current_crn: string;
  current_urn: string;
  requested_name: string;
  requested_crn: string;
  requested_urn: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  reviewed_at: string | null;
  reviewed_by_username: string | null;
}

export async function getEditRequestsForReview(): Promise<EditRequestReviewEntry[]> {
  const { data } = await api.get<EditRequestReviewEntry[]>("/teacher/edit-requests/");
  return data;
}

export async function approveEditRequest(id: number): Promise<EditRequestReviewEntry> {
  const { data } = await api.post<EditRequestReviewEntry>(`/teacher/edit-requests/${id}/approve/`);
  return data;
}

export async function rejectEditRequest(id: number): Promise<EditRequestReviewEntry> {
  const { data } = await api.post<EditRequestReviewEntry>(`/teacher/edit-requests/${id}/reject/`);
  return data;
}

export interface TeacherStudentSummary {
  crn: string;
  roll_number: string;
  name: string;
  section: string;
  email: string;
  contact_number: string;
  photo: string | null;
  trusted_device_bound: boolean;
  trusted_device_bound_at: string | null;
  scan_profile_complete: boolean;
  missing_scan_profile_fields: string[];
}

export interface TeacherStudentAttendanceEntry {
  date: string;
  subject: string;
  section: string;
  marked_at: string;
  ip_address: string | null;
  device_info: string;
}

export interface TeacherStudentDetail extends TeacherStudentSummary {
  username: string;
  course: string;
  semester: number;
  password_note: string;
  attendance: TeacherStudentAttendanceEntry[];
}

export interface TeacherStudentDataResponse {
  sections: string[];
  section: string;
  profile_scan_lock_enabled: boolean;
  students: TeacherStudentSummary[];
  selected_student: TeacherStudentDetail | null;
}

export async function getTeacherStudentData(section?: string, crn?: string): Promise<TeacherStudentDataResponse> {
  const { data } = await api.get<TeacherStudentDataResponse>("/teacher/students/", {
    params: {
      ...(section ? { section } : {}),
      ...(crn ? { crn } : {}),
    },
  });
  return data;
}

export async function resetStudentPasswordToCrn(crn: string): Promise<void> {
  await api.post("/teacher/students/", { crn, action: "reset_password_to_crn" });
}

export async function resetStudentTrustedDevice(crn: string): Promise<void> {
  await api.post("/teacher/students/", { crn, action: "reset_trusted_device" });
}

export async function setProfileScanLock(enabled: boolean): Promise<{ profile_scan_lock_enabled: boolean }> {
  const { data } = await api.post<{ profile_scan_lock_enabled: boolean }>("/teacher/students/", {
    action: "toggle_profile_scan_lock",
    enabled,
  });
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
  present_count: number | null;
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
  const { data } = await api.post(
    "/attendance/mark/",
    { token },
    {
      headers: {
        "X-ClassPulse-Device-ID": getOrCreateDeviceId(),
      },
    }
  );
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

export interface LateEntry {
  date: string;
  subject: string;
  scanned_at: string;
  minutes_late: number;
}

export interface LateStudent {
  name: string;
  crn: string;
  section: string;
  late_count: number;
  max_late: number;
  avg_late: number;
  scan_count: number;
  late_rate: number;
  regular: boolean;
  entries: LateEntry[];
}

export interface LateReportResponse {
  min_minutes: number;
  total_scans: number;
  late_scans: number;
  sections: { section: string; late_students: number; late_scans: number }[];
  students: LateStudent[];
}

export async function getLateReport(
  minMinutes: number,
  section?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<LateReportResponse> {
  const { data } = await api.get<LateReportResponse>("/attendance/late-report/", {
    params: {
      min_minutes: minMinutes,
      ...(section ? { section } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    },
  });
  return data;
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
  // A distinct label for a day the student is known not to be attending
  // (leave, dropped, etc.) - never true at the same time as `present`, and
  // counts exactly like absent for percentages. See NotAttendingMark.
  not_attending: boolean;
  // Only populated on the live-session roster (SessionLiveView) - the
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

export async function markNotAttending(crn: string, section: string, date: string): Promise<void> {
  await api.post("/attendance/day/not-attending/", { crn, section, date });
}

export async function unmarkNotAttending(crn: string, section: string, date: string): Promise<void> {
  await api.delete("/attendance/day/not-attending/", { params: { crn, section, date } });
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

export interface TimetableSlot {
  id: number;
  day_of_week: number;
  day_name: string;
  start_time: string;
  end_time: string;
  section: string;
  subject: string;
}

export type TimetableSlotInput = Omit<TimetableSlot, "id" | "day_name">;

export async function getTimetable(): Promise<TimetableSlot[]> {
  const { data } = await api.get<TimetableSlot[]>("/attendance/timetable/");
  return data;
}

export async function saveTimetableSlot(input: TimetableSlotInput, id?: number): Promise<TimetableSlot> {
  const { data } = id
    ? await api.put<TimetableSlot>(`/attendance/timetable/${id}/`, input)
    : await api.post<TimetableSlot>("/attendance/timetable/", input);
  return data;
}

export async function deleteTimetableSlot(id: number): Promise<void> {
  await api.delete(`/attendance/timetable/${id}/`);
}

export interface Task {
  id: number;
  title: string;
  description: string;
  section: string;
  due_date: string | null;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export type TaskInput = Pick<Task, "title" | "description" | "section" | "due_date">;

export async function getTeacherTasks(section?: string): Promise<Task[]> {
  const { data } = await api.get<Task[]>("/tasks/teacher/", { params: section ? { section } : {} });
  return data;
}

export async function saveTask(input: TaskInput, id?: number): Promise<Task> {
  const { data } = id
    ? await api.patch<Task>(`/tasks/teacher/${id}/`, input)
    : await api.post<Task>("/tasks/teacher/", input);
  return data;
}

export async function deleteTask(id: number): Promise<void> {
  await api.delete(`/tasks/teacher/${id}/`);
}

export async function getStudentTasks(): Promise<Task[]> {
  const { data } = await api.get<Task[]>("/tasks/student/");
  return data;
}

export interface MCQQuestion {
  id: number;
  text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_option: "a" | "b" | "c" | "d";
  is_active: boolean;
  created_at: string;
}

export type MCQQuestionInput = Omit<MCQQuestion, "id" | "created_at">;

export async function getMCQQuestions(): Promise<MCQQuestion[]> {
  const { data } = await api.get<MCQQuestion[]>("/exams/mcq/");
  return data;
}

export async function saveMCQQuestion(input: MCQQuestionInput, id?: number): Promise<MCQQuestion> {
  const { data } = id
    ? await api.patch<MCQQuestion>(`/exams/mcq/${id}/`, input)
    : await api.post<MCQQuestion>("/exams/mcq/", input);
  return data;
}

export async function deleteMCQQuestion(id: number): Promise<void> {
  await api.delete(`/exams/mcq/${id}/`);
}

export interface PracticalQuestion {
  id: number;
  text: string;
  difficulty: "easy" | "hard";
  is_active: boolean;
  created_at: string;
}

export type PracticalQuestionInput = Omit<PracticalQuestion, "id" | "created_at">;

export async function getPracticalQuestions(): Promise<PracticalQuestion[]> {
  const { data } = await api.get<PracticalQuestion[]>("/exams/practical/");
  return data;
}

export async function savePracticalQuestion(input: PracticalQuestionInput, id?: number): Promise<PracticalQuestion> {
  const { data } = id
    ? await api.patch<PracticalQuestion>(`/exams/practical/${id}/`, input)
    : await api.post<PracticalQuestion>("/exams/practical/", input);
  return data;
}

export async function deletePracticalQuestion(id: number): Promise<void> {
  await api.delete(`/exams/practical/${id}/`);
}

export interface Exam {
  id: number;
  title: string;
  section: string;
  easy_practical: number;
  hard_practical: number;
  easy_practical_text: string;
  hard_practical_text: string;
  start_time: string;
  end_time: string;
  manual_status: "auto" | "forced_open" | "forced_closed";
  is_open: boolean;
  created_at: string;
}

export type ExamInput = Pick<
  Exam,
  "title" | "section" | "easy_practical" | "hard_practical" | "start_time" | "end_time" | "manual_status"
>;

export async function getExams(section?: string): Promise<Exam[]> {
  const { data } = await api.get<Exam[]>("/exams/exam/", { params: section ? { section } : {} });
  return data;
}

export async function saveExam(input: ExamInput, id?: number): Promise<Exam> {
  const { data } = id
    ? await api.patch<Exam>(`/exams/exam/${id}/`, input)
    : await api.post<Exam>("/exams/exam/", input);
  return data;
}

export async function setExamManualStatus(
  id: number,
  manual_status: Exam["manual_status"]
): Promise<Exam> {
  const { data } = await api.patch<Exam>(`/exams/exam/${id}/`, { manual_status });
  return data;
}

export async function deleteExam(id: number): Promise<void> {
  await api.delete(`/exams/exam/${id}/`);
}

export interface ExamResultStudent {
  crn: string;
  name: string;
  status: "submitted" | "in_progress";
  score: number | null;
  total: number;
  submitted_at: string | null;
}

export interface ExamResults {
  exam_id: number;
  title: string;
  section: string;
  attempted: number;
  submitted: number;
  average_score: number | null;
  students: ExamResultStudent[];
}

export async function getExamResults(examId: number): Promise<ExamResults> {
  const { data } = await api.get<ExamResults>(`/exams/exam/${examId}/results/`);
  return data;
}

export interface StudentExamSummary {
  id: number;
  title: string;
  section: string;
  start_time: string;
  end_time: string;
  is_open: boolean;
  status: "not_started" | "in_progress" | "submitted";
  score: number | null;
  total: number;
}

export async function getStudentExams(): Promise<StudentExamSummary[]> {
  const { data } = await api.get<StudentExamSummary[]>("/exams/student/exams/");
  return data;
}

export interface StudentMCQ {
  id: number;
  text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
}

export interface ExamAttemptState {
  exam_id: number;
  title: string;
  section: string;
  easy_practical_text: string;
  hard_practical_text: string;
  mcqs: StudentMCQ[];
  answers: Record<string, string>;
  submitted: boolean;
  score: number | null;
  total: number;
  is_open: boolean;
}

export async function startOrResumeExam(examId: number): Promise<ExamAttemptState> {
  const { data } = await api.get<ExamAttemptState>(`/exams/student/exams/${examId}/`);
  return data;
}

export async function saveExamAnswers(
  examId: number,
  answers: Record<string, string>
): Promise<ExamAttemptState> {
  const { data } = await api.patch<ExamAttemptState>(`/exams/student/exams/${examId}/`, { answers });
  return data;
}

export async function submitExam(examId: number): Promise<ExamAttemptState> {
  const { data } = await api.post<ExamAttemptState>(`/exams/student/exams/${examId}/submit/`);
  return data;
}

export interface MCQBulkUploadResult {
  created: number;
  errors: string[];
}

export async function bulkUploadMCQs(file: File): Promise<MCQBulkUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<MCQBulkUploadResult>("/exams/mcq/bulk-upload/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export interface SyllabusCompletionRecord {
  id: number;
  section: string;
  date: string;
  // Present only in the teacher/admin view - students aren't shown this.
  present_count?: number;
  marked_by_name?: string;
  marked_at?: string;
}

export interface SyllabusSession {
  id: number;
  session_number: number;
  topics: string;
  completions: SyllabusCompletionRecord[];
}

export type SyllabusSessionInput = Pick<SyllabusSession, "session_number" | "topics">;

export async function getAttendanceLookup(section: string, date: string): Promise<number | null> {
  const { data } = await api.get<{ present_count: number | null }>("/syllabus/attendance-lookup/", {
    params: { section, date },
  });
  return data.present_count;
}

export async function markSyllabusCompletion(
  sessionId: number,
  input: { section: string; date: string; present_count: number }
): Promise<SyllabusCompletionRecord> {
  const { data } = await api.post<SyllabusCompletionRecord>(`/syllabus/manage/${sessionId}/completion/`, input);
  return data;
}

export async function unmarkSyllabusCompletion(sessionId: number, section: string): Promise<void> {
  await api.delete(`/syllabus/manage/${sessionId}/completion/`, { params: { section } });
}

export async function getSyllabus(): Promise<SyllabusSession[]> {
  const { data } = await api.get<SyllabusSession[]>("/syllabus/");
  return data;
}

export async function saveSyllabusSession(input: SyllabusSessionInput, id?: number): Promise<SyllabusSession> {
  const { data } = id
    ? await api.patch<SyllabusSession>(`/syllabus/manage/${id}/`, input)
    : await api.post<SyllabusSession>("/syllabus/manage/", input);
  return data;
}

export async function deleteSyllabusSession(id: number): Promise<void> {
  await api.delete(`/syllabus/manage/${id}/`);
}

export interface NotAttendingStudent {
  name: string;
  crn: string;
  section: string;
  count: number;
  dates: string[];
}

export interface NotAttendingReportResponse {
  total_marks: number;
  sections: { section: string; students: number; marks: number }[];
  students: NotAttendingStudent[];
}

export async function getNotAttendingReport(
  section?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<NotAttendingReportResponse> {
  const { data } = await api.get<NotAttendingReportResponse>("/attendance/not-attending-report/", {
    params: {
      ...(section ? { section } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    },
  });
  return data;
}
