import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import RegisterPage from "./pages/RegisterPage";
import LoginPage from "./pages/LoginPage";
import StudentProfilePage from "./pages/StudentProfilePage";
import TeacherProfilePage from "./pages/TeacherProfilePage";
import StartAttendancePage from "./pages/teacher/StartAttendancePage";
import LiveQRPage from "./pages/teacher/LiveQRPage";
import ScanQRPage from "./pages/student/ScanQRPage";
import AttendanceHistoryPage from "./pages/student/AttendanceHistoryPage";
import AnalyticsPage from "./pages/teacher/AnalyticsPage";
import DayAttendancePage from "./pages/teacher/DayAttendancePage";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/student/profile" element={<StudentProfilePage />} />
          <Route path="/student/scan" element={<ScanQRPage />} />
          <Route path="/student/history" element={<AttendanceHistoryPage />} />
          <Route path="/teacher/profile" element={<TeacherProfilePage />} />
          <Route path="/teacher/start-attendance" element={<StartAttendancePage />} />
          <Route path="/teacher/session/:sessionId" element={<LiveQRPage />} />
          <Route path="/teacher/analytics" element={<AnalyticsPage />} />
          <Route path="/teacher/day-attendance" element={<DayAttendancePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
