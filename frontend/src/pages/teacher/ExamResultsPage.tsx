import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Alert } from "react-bootstrap";
import { getExamResults, logout } from "../../api/client";
import type { ExamResults } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { formatDateTime } from "../../utils/time";

export default function ExamResultsPage() {
  const { examId } = useParams();
  const [results, setResults] = useState<ExamResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!examId) return;
    getExamResults(Number(examId))
      .then(setResults)
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load results for this exam.");
        }
      });
  }, [examId, navigate]);

  if (!results && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin"
        title={results ? `Results: ${results.title}` : "Exam Results"}
        subtitle={results ? `Section ${results.section}` : undefined}
        actions={
          <Link to="/teacher/exams" className="btn btn-outline-secondary btn-sm">
            ← Back to exams
          </Link>
        }
      />

      {error && <Alert variant="danger">{error}</Alert>}

      {results && (
        <>
          <div className="late-summary">
            <div className="stat-tile">
              <span className="stat-label">Attempted</span>
              <span className="stat-value">{results.attempted}</span>
            </div>
            <div className="stat-tile stat-tile-good">
              <span className="stat-label">Submitted</span>
              <span className="stat-value">{results.submitted}</span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Class average</span>
              <span className="stat-value">{results.average_score ?? "Not yet"}</span>
              <span className="late-of">out of 5 MCQs</span>
            </div>
          </div>

          {results.students.length === 0 ? (
            <div className="empty-state">No student has opened this exam yet.</div>
          ) : (
            <div className="table-responsive">
              <table className="table mb-0">
                <thead>
                  <tr>
                    <th>CRN</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>MCQ score</th>
                    <th>Submitted at</th>
                  </tr>
                </thead>
                <tbody>
                  {results.students.map((s) => (
                    <tr key={s.crn}>
                      <td className="font-mono">{s.crn}</td>
                      <td>{s.name}</td>
                      <td>
                        <span className={`stamp ${s.status === "submitted" ? "stamp-present" : "stamp-neutral"}`}>
                          {s.status === "submitted" ? "Submitted" : "In progress"}
                        </span>
                      </td>
                      <td className="font-mono">{s.score !== null ? `${s.score} / ${s.total}` : "Not submitted"}</td>
                      <td className="text-muted">{s.submitted_at ? formatDateTime(s.submitted_at) : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
