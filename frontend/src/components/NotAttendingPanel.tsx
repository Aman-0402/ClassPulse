import { useEffect, useState } from "react";
import { Alert, Spinner } from "react-bootstrap";
import { getAnalytics, getNotAttendingReport } from "../api/client";
import type { NotAttendingReportResponse } from "../api/client";

interface FlatRow {
  section: string;
  crn: string;
  name: string;
  date: string;
}

function flatten(report: NotAttendingReportResponse): FlatRow[] {
  const rows: FlatRow[] = [];
  for (const student of report.students) {
    for (const date of student.dates) {
      rows.push({ section: student.section, crn: student.crn, name: student.name, date });
    }
  }
  rows.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : a.crn.localeCompare(b.crn)));
  return rows;
}

// Students marked "not attending" (Day-wise Attendance's distinct-from-Absent
// status) - this panel keeps its own section/date filters, independent of
// whatever the rest of the Analytics page is filtered to.
export default function NotAttendingPanel() {
  const [sections, setSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [report, setReport] = useState<NotAttendingReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalytics()
      .then((result) => setSections(result.available_sections))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getNotAttendingReport(section, dateFrom, dateTo)
      .then((result) => {
        if (!active) return;
        setReport(result);
        setError(null);
      })
      .catch(() => active && setError("Could not load the not-attending list."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [section, dateFrom, dateTo]);

  const rows = report ? flatten(report) : [];

  return (
    <section className="late-panel">
      <div className="late-head">
        <div>
          <h2 className="late-title">Not Attending</h2>
          <p className="late-sub">Every student marked "not attending" on Day-wise Attendance, with the date.</p>
        </div>
      </div>

      <div className="filter-bar mb-3">
        <div>
          <label className="small text-muted mb-1 d-block" htmlFor="na-section">
            Section
          </label>
          <select
            id="na-section"
            className="form-select form-select-sm"
            value={section}
            onChange={(e) => setSection(e.target.value)}
          >
            <option value="">All sections</option>
            {sections.map((s) => (
              <option key={s} value={s}>
                Section {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="small text-muted mb-1 d-block" htmlFor="na-from">
            From
          </label>
          <input
            id="na-from"
            type="date"
            className="form-control form-control-sm"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div>
          <label className="small text-muted mb-1 d-block" htmlFor="na-to">
            To
          </label>
          <input
            id="na-to"
            type="date"
            className="form-control form-control-sm"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
        {(section || dateFrom || dateTo) && (
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm align-self-end"
            onClick={() => {
              setSection("");
              setDateFrom("");
              setDateTo("");
            }}
          >
            Clear filters
          </button>
        )}
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

          {rows.length === 0 ? (
            <div className="empty-state">Nobody has been marked not attending for this filter.</div>
          ) : (
            <div className="table-responsive">
              <table className="table mb-0">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Section</th>
                    <th>CRN</th>
                    <th>Name</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr key={`${row.crn}-${row.date}-${index}`}>
                      <td className="font-mono">{row.date}</td>
                      <td>
                        <span className="stamp stamp-neutral">{row.section || "-"}</span>
                      </td>
                      <td className="font-mono">{row.crn}</td>
                      <td>{row.name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
