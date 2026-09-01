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

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingScreen />}>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/student/profile" element={<StudentProfilePage />} />
            <Route path="/student/scan" element={<ScanQRPage />} />
            <Route path="/student/history" element={<AttendanceHistoryPage />} />
            <Route path="/student/change-password" element={<ChangePasswordPage />} />
            <Route path="/teacher/profile" element={<TeacherProfilePage />} />
            <Route path="/teacher/start-attendance" element={<StartAttendancePage />} />
            <Route path="/teacher/session/:sessionId" element={<LiveQRPage />} />
            <Route path="/teacher/analytics" element={<AnalyticsPage />} />
            <Route path="/teacher/day-attendance" element={<DayAttendancePage />} />
            <Route path="/teacher/otp-history" element={<OTPHistoryPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
