import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStudentTasks, logout } from "../../api/client";
import type { Task } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { formatDateTime } from "../../utils/time";

function isOverdue(dueDate: string | null): boolean {
  if (!dueDate) return false;
  return new Date(dueDate + "T23:59:59") < new Date();
}

export default function StudentTasksPage() {
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getStudentTasks()
      .then(setTasks)
      .catch((err) => {
        if (err?.response?.status === 401) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError(err?.response?.data?.detail || "Could not load tasks.");
        }
      });
  }, [navigate]);

  if (!tasks && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Student" title="Tasks" subtitle="Assignments and tasks posted for your section." />

      {error && <div className="empty-state">{error}</div>}

      {tasks && tasks.length === 0 && <div className="empty-state">No tasks posted for your section yet.</div>}

      {tasks && tasks.length > 0 && (
        <div className="tk-list">
          {tasks.map((task) => (
            <div key={task.id} className="tk-card">
              <div className="tk-card-head">
                <h3 className="tk-title">{task.title}</h3>
                {task.due_date && (
                  <span className={`stamp ${isOverdue(task.due_date) ? "stamp-absent" : "stamp-neutral"}`}>
                    Due {task.due_date}
                  </span>
                )}
              </div>
              {task.description && <p className="tk-desc">{task.description}</p>}
              <div className="tk-meta">
                <span>Posted by {task.created_by_name || "—"} · {formatDateTime(task.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
