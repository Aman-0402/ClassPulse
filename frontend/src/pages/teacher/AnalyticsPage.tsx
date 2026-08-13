import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Spinner, Table, Button, ButtonGroup, Alert, Form } from "react-bootstrap";
import { ATTENDANCE_THRESHOLD, getAnalytics, downloadReport, logout } from "../../api/client";
import type { AnalyticsResponse } from "../../api/client";
import AppShell from "../../components/AppShell";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [section, setSection] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<"csv" | "excel" | "pdf" | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    getAnalytics(section)
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
  }, [navigate, section]);

  const handleDownload = async (format: "csv" | "excel" | "pdf") => {
    if (downloadingFormat) return;
    setDownloadError(null);
    setDownloadingFormat(format);
    try {
      await downloadReport(format, section);
    } catch {
      setDownloadError("Could not download the report. Please try again.");
    } finally {
      setDownloadingFormat(null);
    }
  };

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

      {data.below_threshold.length > 0 && (
        <Alert variant="warning">
          {data.below_threshold.length} student(s) below {ATTENDANCE_THRESHOLD}% attendance:{" "}
          {data.below_threshold.map((s) => s.name).join(", ")}
        </Alert>
      )}

      {data.students.length === 0 ? (
        <p className="text-muted">No students in this section yet.</p>
      ) : (
        <Table striped bordered>
          <thead>
            <tr>
              <th>CRN</th>
              <th>Name</th>
              <th>Present</th>
              <th>Total</th>
              <th>%</th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s) => (
              <tr key={s.crn}>
                <td className="font-mono">{s.crn}</td>
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
      )}
    </AppShell>
  );
}
