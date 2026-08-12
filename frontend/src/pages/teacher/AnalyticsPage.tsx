import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Spinner, Table, Badge, Button, ButtonGroup, Alert } from "react-bootstrap";
import { getAnalytics, downloadReport, logout } from "../../api/client";
import type { AnalyticsResponse } from "../../api/client";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
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
    setDownloadError(null);
    try {
      await downloadReport(format);
    } catch {
      setDownloadError("Could not download the report. Please try again.");
    }
  };

  if (!data) return <Spinner animation="border" className="m-4" />;

  return (
    <Container className="py-4">
      <h2>Attendance Analytics</h2>
      <p className="mb-1">Total Sessions: {data.total_sessions}</p>
      <p className="mb-1">Total Students: {data.total_students}</p>
      <p className="mb-3">
        Overall Rate: <Badge bg="info">{data.overall_rate}%</Badge>
      </p>

      {downloadError && <Alert variant="danger">{downloadError}</Alert>}
      <ButtonGroup className="mb-3">
        <Button variant="outline-secondary" onClick={() => handleDownload("csv")}>
          Export CSV
        </Button>
        <Button variant="outline-secondary" onClick={() => handleDownload("excel")}>
          Export Excel
        </Button>
        <Button variant="outline-secondary" onClick={() => handleDownload("pdf")}>
          Export PDF
        </Button>
      </ButtonGroup>

      {data.below_threshold.length > 0 && (
        <Alert variant="warning">
          {data.below_threshold.length} student(s) below 75% attendance:{" "}
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
              <td>{s.crn}</td>
              <td>{s.name}</td>
              <td>{s.present}</td>
              <td>{s.total}</td>
              <td>
                <Badge bg={s.percentage >= 75 ? "success" : "danger"}>{s.percentage}%</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
}
