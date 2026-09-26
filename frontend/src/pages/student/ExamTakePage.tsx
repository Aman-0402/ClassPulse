import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Alert, Form } from "react-bootstrap";
import { logout, saveExamAnswers, startOrResumeExam, submitExam } from "../../api/client";
import type { ExamAttemptState } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { confirmAction, notifyError } from "../../utils/alerts";

const OPTION_LETTERS = ["a", "b", "c", "d"] as const;

export default function ExamTakePage() {
  const { examId } = useParams();
  const [attempt, setAttempt] = useState<ExamAttemptState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => {
    if (!examId) return;
    startOrResumeExam(Number(examId))
      .then(setAttempt)
      .catch((err) => {
        if (err?.response?.status === 401) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError(err?.response?.data?.detail || "Could not load this exam.");
        }
      });
  }, [examId, navigate]);

  useEffect(load, [load]);

  const handleAnswer = async (questionId: number, letter: string) => {
    if (!attempt || !examId) return;
    // Optimistic local update so the radio feels instant, reconciled against
    // the server's response (which is the real source of truth for `answers`).
    setAttempt({ ...attempt, answers: { ...attempt.answers, [questionId]: letter } });
    setSaving(questionId);
    try {
      const updated = await saveExamAnswers(Number(examId), { [questionId]: letter });
      setAttempt(updated);
    } catch (err: any) {
      notifyError("Could Not Save", err?.response?.data?.detail || "Your answer wasn't saved. Try again.");
      load();
    } finally {
      setSaving(null);
    }
  };

  const handleSubmit = async () => {
    if (!attempt || !examId) return;
    const answered = Object.keys(attempt.answers).length;
    const ok = await confirmAction(
      "Submit this exam?",
      answered < attempt.mcqs.length
        ? `You've answered ${answered} of ${attempt.mcqs.length} MCQs. Once submitted, you can't change your answers.`
        : "Once submitted, you can't change your answers.",
      "Submit"
    );
    if (!ok) return;
    setSubmitting(true);
    try {
      const result = await submitExam(Number(examId));
      setAttempt(result);
    } catch {
      notifyError("Submit Failed", "Could not submit the exam. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!attempt && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <PageHeader eyebrow="Student" title="Exam" />
        <Alert variant="danger">{error}</Alert>
        <Link to="/student/exams" className="btn btn-outline-secondary btn-sm">
          Back to exams
        </Link>
      </AppShell>
    );
  }

  const exam = attempt!;
  const locked = exam.submitted;
  const closedButNotSubmitted = !exam.is_open && !exam.submitted;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Student"
        title={exam.title}
        subtitle={`Section ${exam.section} · 5 MCQs, auto-scored, plus 2 practical questions shown below`}
      />

      {exam.submitted && (
        <Alert variant="success">
          Submitted. Your MCQ score: <strong>{exam.score} / {exam.total}</strong>
        </Alert>
      )}
      {closedButNotSubmitted && (
        <Alert variant="warning">
          The exam window has closed. You can still submit the answers you already gave, but can't change them.
        </Alert>
      )}

      <div className="tk-list mb-4">
        {exam.mcqs.map((q, index) => (
          <div key={q.id} className="tk-card">
            <h3 className="tk-title mb-2">
              {index + 1}. {q.text}
            </h3>
            <div className="d-flex flex-column gap-2">
              {OPTION_LETTERS.map((letter) => (
                <Form.Check
                  key={letter}
                  type="radio"
                  id={`q${q.id}-${letter}`}
                  name={`q${q.id}`}
                  label={`${letter.toUpperCase()}. ${q[`option_${letter}`]}`}
                  checked={exam.answers[q.id] === letter}
                  disabled={locked || closedButNotSubmitted || saving === q.id}
                  onChange={() => handleAnswer(q.id, letter)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <PageHeader eyebrow="Practical" title="Practical questions" subtitle="Answer these separately. They are not scored here." />
      <div className="tk-list mb-4">
        <div className="tk-card">
          <div className="tk-card-head">
            <h3 className="tk-title">Easy</h3>
          </div>
          <p className="tk-desc">{exam.easy_practical_text}</p>
        </div>
        <div className="tk-card">
          <div className="tk-card-head">
            <h3 className="tk-title">Hard</h3>
          </div>
          <p className="tk-desc">{exam.hard_practical_text}</p>
        </div>
      </div>

      {!locked && (
        <button type="button" className="cta-button" disabled={submitting} onClick={handleSubmit}>
          {submitting ? "Submitting..." : "Submit Exam"}
        </button>
      )}
    </AppShell>
  );
}
