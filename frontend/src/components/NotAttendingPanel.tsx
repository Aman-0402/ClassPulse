import { Fragment, useEffect, useState } from "react";
import { Alert, Spinner } from "react-bootstrap";
import { getNotAttendingReport } from "../api/client";
import type { NotAttendingReportResponse } from "../api/client";

interface Props {
  section: string;
  dateFrom: string;
  dateTo: string;
}

// Students marked "not attending" (Day-wise Attendance's distinct-from-Absent
// status) in the current filter range — same section/date filters as the
// analytics page above it.
export default function NotAttendingPanel({ section, dateFrom, dateTo }: Props) {
  const [report, setReport] = useState<NotAttendingReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getNotAttendingReport(section, dateFrom, dateTo)
      .then((result) => {
        if (!active) return;
        setReport(result);
        setError(null);
        setOpen(null);
      })
      .catch(() => active && setError("Could not load the not-attending list."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [section, dateFrom, dateTo]);

  return (
    <section className="late-panel">
      <div className="late-head">
        <div>
          <h2 className="late-title">Not Attending</h2>
          <p className="late-sub">Students marked "not attending" on Day-wise Attendance, for this filter.</p>
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {loading && !report && <Spinner animation="border" size="sm" />}

      {report && (
        <>
          <div className="late-summary">
            <div className="stat-tile">
              <span className="stat-label">Total marks</span>
              <span className="stat-value">{report.total_marks}</span>
            </div>
            <div className="stat-tile stat-tile-bad">
              <span className="stat-label">Students</span>
              <span className="stat-value">{report.students.length}</span>
            </div>
            {report.sections.map((s) => (
              <div key={s.section} className="stat-tile">
                <span className="stat-label">Section {s.section}</span>
                <span className="stat-value">{s.students}</span>
                <span className="late-of">
                  student{s.students === 1 ? "" : "s"} · {s.marks} mark{s.marks === 1 ? "" : "s"}
                </span>
              </div>
            ))}
          </div>

          {report.students.length === 0 ? (
            <div className="empty-state">Nobody has been marked not attending for this filter.</div>
          ) : (
            <div className="table-responsive">
              <table className="table mb-0">
                <thead>
                  <tr>
                    <th>Section</th>
                    <th>CRN</th>
                    <th>Name</th>
                    <th>Times marked</th>
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
                          <td>
                            <span className="stamp stamp-not-attending">{student.count}</span>
                          </td>
                          <td className="text-end text-muted">{expanded ? "Hide ▴" : "Details ▾"}</td>
                        </tr>
                        {expanded && (
                          <tr className="late-detail">
                            <td colSpan={5}>
                              <ul className="late-entries">
                                {student.dates.map((date) => (
                                  <li key={date}>
                                    <span className="font-mono">{date}</span>
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
