import { Fragment, useEffect, useState } from "react";
import { Alert, Spinner } from "react-bootstrap";
import { getLateReport } from "../api/client";
import type { LateReportResponse } from "../api/client";
import { formatDateTime } from "../utils/time";

// 0 = list every scan time, not just late ones.
const THRESHOLDS = [
  { minutes: 5, label: "5+ min" },
  { minutes: 10, label: "10+ min" },
  { minutes: 15, label: "15+ min" },
  { minutes: 30, label: "30+ min" },
  { minutes: 0, label: "All scans" },
];

interface Props {
  section: string;
  dateFrom: string;
  dateTo: string;
}

function csvCell(value: string | number): string {
  return `"${String(value).replace(/"/g, '""')}"`;
}

function downloadCsv(report: LateReportResponse) {
  const rows = [["Section", "CRN", "Name", "Date", "Subject", "Scanned at", "Minutes after start"]];
  for (const student of report.students) {
    for (const entry of student.entries) {
      rows.push([
        student.section,
        student.crn,
        student.name,
        entry.date,
        entry.subject,
        formatDateTime(entry.scanned_at),
        String(entry.minutes_late),
      ]);
    }
  }
  const blob = new Blob([rows.map((r) => r.map(csvCell).join(",")).join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `late-arrivals-${report.min_minutes}min.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

// Who scanned in late, grouped by student, using the same section/date filters as
// the analytics page above it. "Late" is measured from when the teacher opened
// the session's QR to the student's own scan.
export default function LateArrivalsPanel({ section, dateFrom, dateTo }: Props) {
  const [minutes, setMinutes] = useState(10);
  const [report, setReport] = useState<LateReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getLateReport(minutes, section, dateFrom, dateTo)
      .then((result) => {
        if (!active) return;
        setReport(result);
        setError(null);
        setOpen(null);
      })
      .catch(() => active && setError("Could not load the late arrivals report."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [minutes, section, dateFrom, dateTo]);

  const everyScan = minutes === 0;

  return (
    <section className="late-panel">
      <div className="late-head">
        <div>
          <h2 className="late-title">{everyScan ? "Scan times" : "Late arrivals"}</h2>
          <p className="late-sub">
            {everyScan
              ? "Every student's scan time, in minutes after the session started."
              : `Students who scanned ${minutes} or more minutes after the session started.`}
          </p>
        </div>
        <div className="late-controls">
          <div className="sa-chips late-chips" role="radiogroup" aria-label="Late by">
            {THRESHOLDS.map((t) => (
              <button
                key={t.minutes}
                type="button"
                role="radio"
                aria-checked={minutes === t.minutes}
                className={`late-chip ${minutes === t.minutes ? "late-chip-on" : ""}`}
                onClick={() => setMinutes(t.minutes)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            disabled={!report || report.students.length === 0}
            onClick={() => report && downloadCsv(report)}
          >
            Export CSV
          </button>
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {loading && !report && <Spinner animation="border" size="sm" />}

      {report && (
        <>
          <div className="late-summary">
            <div className="stat-tile">
              <span className="stat-label">{everyScan ? "Scans" : "Late scans"}</span>
              <span className="stat-value">{report.late_scans}</span>
              <span className="late-of">of {report.total_scans} total scans</span>
            </div>
            <div className="stat-tile stat-tile-bad">
              <span className="stat-label">Students</span>
              <span className="stat-value">{report.students.length}</span>
            </div>
            {report.sections.map((s) => (
              <div key={s.section} className="stat-tile">
                <span className="stat-label">Section {s.section}</span>
                <span className="stat-value">{s.late_students}</span>
                <span className="late-of">
                  student{s.late_students === 1 ? "" : "s"} · {s.late_scans} scan{s.late_scans === 1 ? "" : "s"}
                </span>
              </div>
            ))}
          </div>

          {report.students.length === 0 ? (
            <div className="empty-state">
              {everyScan ? "No scans recorded for this filter." : `Nobody scanned ${minutes}+ minutes late for this filter.`}
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table mb-0">
                <thead>
                  <tr>
                    <th>Section</th>
                    <th>CRN</th>
                    <th>Name</th>
                    <th>{everyScan ? "Scans" : "Times late"}</th>
                    <th>Avg (min)</th>
                    <th>Worst (min)</th>
                    <th aria-label="Details" />
                  </tr>
                </thead>
                <tbody>
                  {report.students.map((student) => {
                    const expanded = open === student.crn;
                    return (
                      <Fragment key={student.crn}>
                        <tr className="late-row" onClick={() => setOpen(expanded ? null : student.crn)}>
                          <td>
                            <span className="stamp stamp-neutral">{student.section || "-"}</span>
                          </td>
                          <td className="font-mono">{student.crn}</td>
                          <td>{student.name}</td>
                          <td>{student.late_count}</td>
                          <td className="font-mono">{student.avg_late}</td>
                          <td>
                            <span className={`late-badge ${student.max_late >= 15 ? "late-badge-bad" : ""}`}>
                              {student.max_late}
                            </span>
                          </td>
                          <td className="text-end text-muted">{expanded ? "Hide ▴" : "Details ▾"}</td>
                        </tr>
                        {expanded && (
                          <tr className="late-detail">
                            <td colSpan={7}>
                              <ul className="late-entries">
                                {student.entries.map((entry, i) => (
                                  <li key={`${entry.scanned_at}-${i}`}>
                                    <span className="font-mono">{entry.date}</span>
                                    <span>{entry.subject}</span>
                                    <span className="text-muted">scanned {formatDateTime(entry.scanned_at)}</span>
                                    <strong>{entry.minutes_late} min after start</strong>
                                  </li>
                                ))}
                              </ul>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
