import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Spinner, Table, Badge } from "react-bootstrap";
import { getStudentHistory, logout } from "../../api/client";
import type { AttendanceHistoryResponse } from "../../api/client";

export default function AttendanceHistoryPage() {
  const [data, setData] = useState<AttendanceHistoryResponse | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getStudentHistory()
      .then(setData)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  if (!data) return <Spinner animation="border" className="m-4" />;

  return (
    <Container className="py-4">
      <h2>Attendance History</h2>
      <p className="mb-1">Total Classes: {data.total}</p>
      <p className="mb-1">Present: {data.present}</p>
      <p className="mb-3">
        Attendance: <Badge bg={data.percentage >= 75 ? "success" : "danger"}>{data.percentage}%</Badge>
      </p>
      <Table striped bordered>
        <thead>
          <tr>
            <th>Date</th>
            <th>Subject</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data.history.map((entry, index) => (
            <tr key={`${entry.date}-${index}`}>
              <td>{entry.date}</td>
              <td>{entry.subject}</td>
              <td>
                <Badge bg={entry.status === "present" ? "success" : "danger"}>{entry.status}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
}
