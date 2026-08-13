import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Spinner, Table, Button, ButtonGroup, Alert } from "react-bootstrap";
import { ATTENDANCE_THRESHOLD, getAnalytics, downloadReport, logout } from "../../api/client";
import type { AnalyticsResponse } from "../../api/client";
import AppShell from "../../components/AppShell";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<"csv" | "excel" | "pdf" | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  const handleDownload = async (format: "csv" | "excel" | "pdf") => {
    if (downloadingFormat) return;
    setDownloadError(null);
    setDownloadingFormat(format);
    try {
      await downloadReport(format);
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
      <h1 className="h3 mb-4">Attendance Analytics</h1>
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
    </AppShell>
  );
}
