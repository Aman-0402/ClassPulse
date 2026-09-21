import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Alert } from "react-bootstrap";
import { getAnalytics, getCurrentSchedule, startSession, logout } from "../../api/client";
import AppShell from "../../components/AppShell";
import { TRAINING_SUBJECT } from "../../constants";

const SUBJECT = TRAINING_SUBJECT;
const DURATION_OPTIONS = [5, 10, 15, 30, 60];

interface PrefillState {
  subject: string;
  section: string;
  periods: number;
}

export default function StartAttendancePage() {
  const location = useLocation();
  const prefill = location.state as PrefillState | null;

  const [sections, setSections] = useState<string[]>([]);
  const [section, setSection] = useState(prefill?.section ?? "");
  const [duration, setDuration] = useState(5);
  const [merged, setMerged] = useState(prefill?.periods === 2);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [scheduleHint, setScheduleHint] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getAnalytics()
      .then((result) => setSections(result.available_sections))
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        }
      });

    if (prefill) {
      setScheduleHint(`From today's timetable: BBA III ${prefill.section}`);
      return;
    }
    getCurrentSchedule()
      .then((data) => {
        if (data.matched && data.section) {
          setSection(data.section);
          setScheduleHint(`Auto-filled from today's timetable: BBA III ${data.section}`);
        }
      })
      .catch(() => {
        // Timetable auto-fill is a convenience, not required — the form still works blank.
      });
    // Only re-run when this page is opened without a specific slot pre-filled.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!section) {
      setError("Choose a section first.");
      return;
    }
    setStarting(true);
    try {
      const session = await startSession(SUBJECT, duration, merged ? 2 : 1, section);
      navigate(`/teacher/session/${session.id}`);
    } catch {
      setError("Could not start attendance session.");
    } finally {
      setStarting(false);
    }
  };

  return (
    <AppShell>
      <div className="sa-head">
        <h1 className="h3 mb-1">Start Attendance</h1>
        <p className="text-muted mb-0">Pick a section and how long students have to scan. A live QR opens next.</p>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {scheduleHint && <Alert variant="info">{scheduleHint}</Alert>}

      <form className="sa-layout" onSubmit={handleSubmit}>
        <div className="sa-form">
          <section className="sa-step">
            <div className="sa-step-title">
              <span className="sa-step-num">1</span> Section
            </div>
            {sections.length === 0 ? (
              <p className="text-muted mb-0">Loading sections...</p>
            ) : (
              <div className="sa-chips" role="radiogroup" aria-label="Section">
                {sections.map((s) => (
                  <button
                    key={s}
                    type="button"
                    role="radio"
                    aria-checked={section === s}
                    className={`sa-chip ${section === s ? "sa-chip-on" : ""}`}
                    onClick={() => setSection(s)}
                  >
                    <span className="sa-chip-small">BBA III</span>
                    <span className="sa-chip-big">{s}</span>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="sa-step">
            <div className="sa-step-title">
              <span className="sa-step-num">2</span> Attendance window
            </div>
            <div className="sa-chips" role="radiogroup" aria-label="Attendance window">
              {DURATION_OPTIONS.map((minutes) => (
                <button
                  key={minutes}
                  type="button"
                  role="radio"
                  aria-checked={duration === minutes}
                  className={`sa-chip ${duration === minutes ? "sa-chip-on" : ""}`}
                  onClick={() => setDuration(minutes)}
                >
                  <span className="sa-chip-big">{minutes}</span>
                  <span className="sa-chip-small">min</span>
                </button>
              ))}
            </div>
            <p className="sa-help">Students can mark attendance until this window closes.</p>
          </section>

          <section className="sa-step">
            <div className="sa-step-title">
              <span className="sa-step-num">3</span> Periods
            </div>
            <div className="sa-segment" role="radiogroup" aria-label="Periods">
              <button
                type="button"
                role="radio"
                aria-checked={!merged}
                className={!merged ? "sa-segment-on" : ""}
                onClick={() => setMerged(false)}
              >
                Single period
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={merged}
                className={merged ? "sa-segment-on" : ""}
                onClick={() => setMerged(true)}
              >
                Double period
              </button>
            </div>
            <p className="sa-help">
              {merged
                ? "One QR scan marks attendance for both periods, and it counts as 2 sessions in reports."
                : "One QR scan marks attendance for this period."}
            </p>
          </section>
        </div>

        <aside className="sa-summary">
          <div className="sa-summary-label">Session summary</div>
          <div className="sa-summary-subject">{SUBJECT}</div>
          <dl className="sa-summary-list">
            <div>
              <dt>Section</dt>
              <dd>{section ? `BBA III ${section}` : "Not chosen"}</dd>
            </div>
            <div>
              <dt>Window</dt>
              <dd>{duration} minutes</dd>
            </div>
            <div>
              <dt>Counts as</dt>
              <dd>{merged ? "2 sessions" : "1 session"}</dd>
            </div>
          </dl>
          <p className="sa-summary-note">
            {section ? `Only Section ${section} students can mark this attendance.` : "Choose a section to continue."}
          </p>
          <button type="submit" className="sa-start" disabled={starting || !section}>
            {starting ? "Starting..." : "Start Session"}
          </button>
        </aside>
      </form>
    </AppShell>
  );
}
