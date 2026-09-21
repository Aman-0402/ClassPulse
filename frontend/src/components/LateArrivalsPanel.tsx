import { Fragment, useEffect, useMemo, useState } from "react";
import { Alert, Spinner } from "react-bootstrap";
import { getLateReport } from "../api/client";
import type { LateReportResponse, LateStudent } from "../api/client";
import { formatDateTime } from "../utils/time";

// 0 = list every scan time, not just late ones.
const THRESHOLDS = [
  { minutes: 5, label: "5+ min" },
  { minutes: 10, label: "10+ min" },
  { minutes: 15, label: "15+ min" },
  { minutes: 30, label: "30+ min" },
  { minutes: 0, label: "All scans" },
];

type SortKey = "late_count" | "late_rate" | "avg_late" | "max_late";

const SORT_LABELS: Record<SortKey, string> = {
  late_count: "Times late",
  late_rate: "Late rate",
  avg_late: "Avg (min)",
  max_late: "Worst (min)",
};

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
  const [sortKey, setSortKey] = useState<SortKey>("late_count");

  const sorted = useMemo<LateStudent[]>(() => {
    if (!report) return [];
    return [...report.students].sort((a, b) => b[sortKey] - a[sortKey] || b.late_count - a.late_count);
  }, [report, sortKey]);
  const regularCount = report ? report.students.filter((s) => s.regular).length : 0;
  const worst = report && report.students.length > 0
    ? report.students.reduce((top, s) => (s.max_late > top.max_late ? s : top))
    : null;

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
            {!everyScan && (
              <div className="stat-tile stat-tile-bad">
                <span className="stat-label">Regularly late</span>
                <span className="stat-value">{regularCount}</span>
                <span className="late-of">3+ times and over half their scans</span>
              </div>
            )}
            {worst && (
              <div className="stat-tile stat-tile-bad">
                <span className="stat-label">Longest delay</span>
                <span className="stat-value">{worst.max_late} min</span>
                <span className="late-of">{worst.name} · {worst.crn}</span>
              </div>
            )}
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
                    {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
                      <th key={key} aria-sort={sortKey === key ? "descending" : "none"}>
                        <button
                          type="button"
                          className={`late-sort ${sortKey === key ? "late-sort-on" : ""}`}
                          onClick={() => setSortKey(key)}
                        >
                          {key === "late_count" && everyScan ? "Scans" : SORT_LABELS[key]}
                          {sortKey === key ? " ▾" : ""}
                        </button>
                      </th>
                    ))}
                    <th aria-label="Details" />
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((student) => {
                    const expanded = open === student.crn;
                    return (
                      <Fragment key={student.crn}>
                        <tr className="late-row" onClick={() => setOpen(expanded ? null : student.crn)}>
                          <td>
                            <span className="stamp stamp-neutral">{student.section || "-"}</span>
                          </td>
                          <td className="font-mono">{student.crn}</td>
                          <td>
                            {student.name}
                            {student.regular && !everyScan && <span className="late-regular">Regular</span>}
                          </td>
                          <td>
                            {student.late_count}
                            <span className="late-of"> of {student.scan_count}</span>
                          </td>
                          <td>
                            <span className="late-rate">
                              <span className="late-rate-bar" style={{ width: `${Math.min(student.late_rate, 100)}%` }} />
                            </span>
                            <span className="font-mono ms-2">{student.late_rate}%</span>
                          </td>
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
                            <td colSpan={8}>
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
