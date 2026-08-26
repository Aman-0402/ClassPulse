import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Spinner, Table, Button, ButtonGroup, Alert, Form } from "react-bootstrap";
import { ATTENDANCE_THRESHOLD, getAnalytics, downloadReport, logout } from "../../api/client";
import type { AnalyticsResponse } from "../../api/client";
import AppShell from "../../components/AppShell";
import TablePagination from "../../components/TablePagination";

const PAGE_SIZE = 70;

function toIsoDate(d: Date): string {
  const offset = d.getTimezoneOffset();
  return new Date(d.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function startOfWeek(): string {
  const now = new Date();
  const day = now.getDay(); // 0 = Sunday
  const diffToMonday = day === 0 ? 6 : day - 1;
  const monday = new Date(now);
  monday.setDate(now.getDate() - diffToMonday);
  return toIsoDate(monday);
}

function startOfMonth(): string {
  const now = new Date();
  return toIsoDate(new Date(now.getFullYear(), now.getMonth(), 1));
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [section, setSection] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<"csv" | "excel" | "pdf" | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    getAnalytics(section, dateFrom, dateTo)
      .then((result) => {
        if (active) {
          setData(result);
          setLoadError(null);
        }
      })
      .catch((err) => {
        if (!active) return;
        // A missing/unauthorized session should log out; a bad filter value should not.
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setLoadError("Could not load analytics for this filter.");
        }
      });
    return () => {
      active = false;
    };
  }, [navigate, section, dateFrom, dateTo]);

  useEffect(() => {
    setPage(1);
  }, [section, dateFrom, dateTo, search]);

  const handleDownload = async (format: "csv" | "excel" | "pdf") => {
    if (downloadingFormat) return;
    setDownloadError(null);
    setDownloadingFormat(format);
    try {
      await downloadReport(format, section, dateFrom, dateTo);
    } catch {
      setDownloadError("Could not download the report. Please try again.");
    } finally {
      setDownloadingFormat(null);
    }
  };

  const applyPreset = (preset: "week" | "month" | "all") => {
    if (preset === "week") {
      setDateFrom(startOfWeek());
      setDateTo(toIsoDate(new Date()));
    } else if (preset === "month") {
      setDateFrom(startOfMonth());
      setDateTo(toIsoDate(new Date()));
    } else {
      setDateFrom("");
      setDateTo("");
    }
  };

  const activePreset =
    dateFrom === "" && dateTo === ""
      ? "all"
      : dateFrom === startOfWeek() && dateTo === toIsoDate(new Date())
      ? "week"
      : dateFrom === startOfMonth() && dateTo === toIsoDate(new Date())
      ? "month"
      : null;

  if (!data) {
    return (
      <AppShell>
        <Spinner animation="border" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="d-flex justify-content-between align-items-end mb-4 flex-wrap gap-2">
        <h1 className="h3 mb-0">Attendance Analytics</h1>
        <div className="d-flex gap-2 flex-wrap">
          <Form.Group controlId="student-search" style={{ minWidth: 220 }}>
            <Form.Label className="small text-muted mb-1">Search student</Form.Label>
            <Form.Control
              type="search"
              placeholder="Name or CRN"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </Form.Group>
          <Form.Group controlId="section-filter" style={{ minWidth: 180 }}>
            <Form.Label className="small text-muted mb-1">Section</Form.Label>
            <Form.Select value={section} onChange={(e) => setSection(e.target.value)}>
              <option value="">All sections</option>
              {data.available_sections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
        </div>
      </div>

      <div className="d-flex align-items-end gap-2 flex-wrap mb-4">
        <Form.Group controlId="date-from" style={{ minWidth: 160 }}>
          <Form.Label className="small text-muted mb-1">From</Form.Label>
          <Form.Control type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </Form.Group>
        <Form.Group controlId="date-to" style={{ minWidth: 160 }}>
          <Form.Label className="small text-muted mb-1">To</Form.Label>
          <Form.Control type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </Form.Group>
        <ButtonGroup>
          <Button
            variant={activePreset === "week" ? "dark" : "outline-secondary"}
            onClick={() => applyPreset("week")}
          >
            This Week
          </Button>
          <Button
            variant={activePreset === "month" ? "dark" : "outline-secondary"}
            onClick={() => applyPreset("month")}
          >
            This Month
          </Button>
          <Button
            variant={activePreset === "all" ? "dark" : "outline-secondary"}
            onClick={() => applyPreset("all")}
          >
            All Time
          </Button>
        </ButtonGroup>
      </div>

      {loadError && <Alert variant="danger">{loadError}</Alert>}

      <Card className="mb-4" style={{ maxWidth: 480 }}>
        <Card.Body className="d-flex justify-content-between align-items-center">
          <div>
            <div className="text-muted small">Total Sessions</div>
            <div className="fs-4 font-mono">{data.total_sessions}</div>
          </div>
          <div>
            <div className="text-muted small">Total Students</div>
            <div className="fs-4 font-mono">{data.total_students}</div>
          </div>
          <span className={`stamp ${data.overall_rate >= ATTENDANCE_THRESHOLD ? "stamp-present" : "stamp-absent"}`}>
            {data.overall_rate}%
          </span>
        </Card.Body>
      </Card>

      {downloadError && <Alert variant="danger">{downloadError}</Alert>}
      <ButtonGroup className="mb-3">
        <Button variant="outline-secondary" disabled={!!downloadingFormat} onClick={() => handleDownload("csv")}>
          {downloadingFormat === "csv" ? "Exporting..." : "Export CSV"}
        </Button>
        <Button variant="outline-secondary" disabled={!!downloadingFormat} onClick={() => handleDownload("excel")}>
          {downloadingFormat === "excel" ? "Exporting..." : "Export Excel"}
        </Button>
        <Button variant="outline-secondary" disabled={!!downloadingFormat} onClick={() => handleDownload("pdf")}>
          {downloadingFormat === "pdf" ? "Exporting..." : "Export PDF"}
        </Button>
      </ButtonGroup>

      {(() => {
        const query = search.trim().toLowerCase();
        const visibleStudents = query
          ? data.students.filter(
              (s) => s.name.toLowerCase().includes(query) || s.crn.toLowerCase().includes(query)
            )
          : data.students;

        if (data.students.length === 0) {
          return <p className="text-muted">No students in this section yet.</p>;
        }
        if (visibleStudents.length === 0) {
          return <p className="text-muted">No students match "{search}".</p>;
        }

        const totalPages = Math.max(1, Math.ceil(visibleStudents.length / PAGE_SIZE));
        const pageStudents = visibleStudents.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

        return (
          <>
            <div className="table-responsive">
              <Table striped bordered>
                <thead>
                  <tr>
                    <th>S.No</th>
                    <th>CRN</th>
                    <th>Roll No.</th>
                    <th>Name</th>
                    <th>Present</th>
                    <th>Total</th>
                    <th>%</th>
                  </tr>
                </thead>
                <tbody>
                  {pageStudents.map((s, index) => (
                    <tr key={s.crn}>
                      <td>{(page - 1) * PAGE_SIZE + index + 1}</td>
                      <td className="font-mono">{s.crn}</td>
                      <td className="font-mono">{s.roll_number}</td>
                      <td>{s.name}</td>
                      <td>{s.present}</td>
                      <td>{s.total}</td>
                      <td>
                        <span className={`stamp ${s.percentage >= ATTENDANCE_THRESHOLD ? "stamp-present" : "stamp-absent"}`}>
                          {s.percentage}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
            <TablePagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        );
      })()}
    </AppShell>
  );
}
