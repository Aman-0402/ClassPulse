import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getStudentExams, logout } from "../../api/client";
import type { StudentExamSummary } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { formatDateTime } from "../../utils/time";

const STATUS_LABEL: Record<StudentExamSummary["status"], string> = {
  not_started: "Not started",
  in_progress: "In progress",
  submitted: "Submitted",
};

export default function StudentExamsPage() {
  const [exams, setExams] = useState<StudentExamSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getStudentExams()
      .then(setExams)
      .catch((err) => {
        if (err?.response?.status === 401) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError(err?.response?.data?.detail || "Could not load exams.");
        }
      });
  }, [navigate]);

  if (!exams && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Student" title="Exams" subtitle="Exams scheduled for your section." />

      {error && <div className="empty-state">{error}</div>}
      {exams && exams.length === 0 && <div className="empty-state">No exams scheduled for your section yet.</div>}

      {exams && exams.length > 0 && (
        <div className="tk-list">
          {exams.map((exam) => {
            const canEnter = exam.is_open || exam.status !== "not_started";
            return (
              <div key={exam.id} className="tk-card">
                <div className="tk-card-head">
                  <h3 className="tk-title">{exam.title}</h3>
                  <span
                    className={`stamp ${
                      exam.status === "submitted"
                        ? "stamp-present"
                        : exam.is_open
                        ? "stamp-neutral"
                        : "stamp-absent"
                    }`}
                  >
                    {exam.status === "submitted" ? "Submitted" : exam.is_open ? "Open now" : "Closed"}
                  </span>
                </div>
                <p className="tk-desc">
                  {formatDateTime(exam.start_time)} → {formatDateTime(exam.end_time)}
                </p>
                <div className="tk-meta">
                  <span>
                    {STATUS_LABEL[exam.status]}
                    {exam.status === "submitted" && exam.score !== null && ` · Score: ${exam.score} / ${exam.total}`}
                  </span>
                  {canEnter ? (
                    <Link to={`/student/exams/${exam.id}`} className="btn btn-sm btn-outline-secondary">
                      {exam.status === "submitted" ? "View result" : exam.status === "in_progress" ? "Resume" : "Start"}
                    </Link>
                  ) : (
                    <span className="text-muted small">Not open yet</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
