import { useEffect } from "react";
import Swal from "sweetalert2";
import { useNavigate } from "react-router-dom";
import { getStudentTasks } from "../api/client";
import { getRole } from "../utils/session";

const LAST_SEEN_KEY = "classpulse_last_seen_task_id";

// Pops a SweetAlert2 the first time a student sees a task added since their
// last visit — not on every page (AppShell remounts on every route change,
// since it isn't a persistent layout), just once per new task, ever, tracked
// by the highest task id already shown. A brand-new student's existing tasks
// aren't announced as "new" — only ones added after their first login are.
export default function NewTaskNotifier() {
  const navigate = useNavigate();

  useEffect(() => {
    if (getRole() !== "student") return;

    getStudentTasks()
      .then((tasks) => {
        if (tasks.length === 0) return;
        const maxId = Math.max(...tasks.map((t) => t.id));
        const stored = localStorage.getItem(LAST_SEEN_KEY);

        if (stored === null) {
          // First time ever seen on this device — establish the baseline
          // quietly, don't announce every pre-existing task as "new".
          localStorage.setItem(LAST_SEEN_KEY, String(maxId));
          return;
        }

        const lastSeen = Number(stored);
        const newTasks = tasks.filter((t) => t.id > lastSeen);
        if (newTasks.length === 0) return;

        localStorage.setItem(LAST_SEEN_KEY, String(maxId));

        const title = newTasks.length === 1 ? "New Task Posted" : `${newTasks.length} New Tasks Posted`;
        const html =
          newTasks.length === 1
            ? `<strong>${newTasks[0].title}</strong>${newTasks[0].due_date ? `<br><span style="color:#75648f">Due ${newTasks[0].due_date}</span>` : ""}`
            : `<ul style="text-align:left;padding-left:1.2em;margin:0">${newTasks
                .map((t) => `<li>${t.title}${t.due_date ? ` — due ${t.due_date}` : ""}</li>`)
                .join("")}</ul>`;

        Swal.fire({
          icon: "info",
          title,
          html,
          confirmButtonText: "View Tasks",
          confirmButtonColor: "#9d5fd1",
          showCancelButton: true,
          cancelButtonText: "Later",
        }).then((result) => {
          if (result.isConfirmed) navigate("/student/tasks");
        });
      })
      .catch(() => {
        // Best-effort — a failed check just means no popup this time, never blocks the page.
      });
    // Runs once per mount; AppShell remounts per route, but the localStorage
    // guard above already makes repeat mounts a no-op once caught up.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
