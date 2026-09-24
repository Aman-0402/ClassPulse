import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import LoadingScreen from "./components/LoadingScreen";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const StudentProfilePage = lazy(() => import("./pages/StudentProfilePage"));
const TeacherProfilePage = lazy(() => import("./pages/TeacherProfilePage"));
const StartAttendancePage = lazy(() => import("./pages/teacher/StartAttendancePage"));
const LiveQRPage = lazy(() => import("./pages/teacher/LiveQRPage"));
const ScanQRPage = lazy(() => import("./pages/student/ScanQRPage"));
const AttendanceHistoryPage = lazy(() => import("./pages/student/AttendanceHistoryPage"));
const ChangePasswordPage = lazy(() => import("./pages/student/ChangePasswordPage"));
const AnalyticsPage = lazy(() => import("./pages/teacher/AnalyticsPage"));
const DayAttendancePage = lazy(() => import("./pages/teacher/DayAttendancePage"));
const OTPHistoryPage = lazy(() => import("./pages/teacher/OTPHistoryPage"));
const StudentDataPage = lazy(() => import("./pages/teacher/StudentDataPage"));
const TimetablePage = lazy(() => import("./pages/teacher/TimetablePage"));
const ProfileCorrectionsPage = lazy(() => import("./pages/teacher/ProfileCorrectionsPage"));
const TeacherTasksPage = lazy(() => import("./pages/teacher/TasksPage"));
const QuestionBankPage = lazy(() => import("./pages/teacher/QuestionBankPage"));
const ExamsPage = lazy(() => import("./pages/teacher/ExamsPage"));
const ExamResultsPage = lazy(() => import("./pages/teacher/ExamResultsPage"));
const StudentTasksPage = lazy(() => import("./pages/student/TasksPage"));
const StudentExamsPage = lazy(() => import("./pages/student/ExamsPage"));
const ExamTakePage = lazy(() => import("./pages/student/ExamTakePage"));
const SyllabusPage = lazy(() => import("./pages/SyllabusPage"));

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingScreen />}>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/syllabus" element={<SyllabusPage />} />
            <Route path="/student/profile" element={<StudentProfilePage />} />
            <Route path="/student/scan" element={<ScanQRPage />} />
            <Route path="/student/history" element={<AttendanceHistoryPage />} />
            <Route path="/student/change-password" element={<ChangePasswordPage />} />
            <Route path="/student/tasks" element={<StudentTasksPage />} />
            <Route path="/student/exams" element={<StudentExamsPage />} />
            <Route path="/student/exams/:examId" element={<ExamTakePage />} />
            <Route path="/teacher/profile" element={<TeacherProfilePage />} />
            <Route path="/teacher/start-attendance" element={<StartAttendancePage />} />
            <Route path="/teacher/session/:sessionId" element={<LiveQRPage />} />
            <Route path="/teacher/analytics" element={<AnalyticsPage />} />
            <Route path="/teacher/day-attendance" element={<DayAttendancePage />} />
            <Route path="/teacher/otp-history" element={<OTPHistoryPage />} />
            <Route path="/teacher/students" element={<StudentDataPage />} />
            <Route path="/teacher/timetable" element={<TimetablePage />} />
            <Route path="/teacher/corrections" element={<ProfileCorrectionsPage />} />
            <Route path="/teacher/tasks" element={<TeacherTasksPage />} />
            <Route path="/teacher/question-bank" element={<QuestionBankPage />} />
            <Route path="/teacher/exams" element={<ExamsPage />} />
            <Route path="/teacher/exams/:examId/results" element={<ExamResultsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
