import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, ButtonGroup, Card } from "react-bootstrap";
import {
  approveEditRequest,
  getEditRequestsForReview,
  logout,
  rejectEditRequest,
} from "../../api/client";
import type { EditRequestReviewEntry } from "../../api/client";
import AppShell from "../../components/AppShell";
import PageHeader from "../../components/PageHeader";
import LoadingScreen from "../../components/LoadingScreen";
import { confirmAction, notifyError, notifySuccess } from "../../utils/alerts";
import { formatDateTime } from "../../utils/time";

const STATUS_STAMP: Record<EditRequestReviewEntry["status"], string> = {
  pending: "stamp-neutral",
  approved: "stamp-present",
  rejected: "stamp-absent",
};

interface Change {
  label: string;
  from: string;
  to: string;
}

// Only the fields the student actually asked to change - a blank requested_*
// means "leave this alone", not "clear it".
function changesFor(entry: EditRequestReviewEntry): Change[] {
  const changes: Change[] = [];
  if (entry.requested_name) changes.push({ label: "Name", from: entry.full_name, to: entry.requested_name });
  if (entry.requested_crn) changes.push({ label: "CRN", from: entry.current_crn, to: entry.requested_crn });
  if (entry.requested_urn) changes.push({ label: "Roll No.", from: entry.current_urn, to: entry.requested_urn });
  return changes;
}

export default function ProfileCorrectionsPage() {
  const [entries, setEntries] = useState<EditRequestReviewEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [busyId, setBusyId] = useState<number | null>(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    return getEditRequestsForReview()
      .then((data) => {
        setEntries(data);
        setError(null);
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load profile correction requests.");
        }
      });
  }, [navigate]);

  useEffect(() => {
    load();
  }, [load]);

  const review = async (entry: EditRequestReviewEntry, action: "approve" | "reject") => {
    const changes = changesFor(entry);
    const summary = changes.map((c) => `${c.label}: ${c.from || "(blank)"} → ${c.to}`).join("\n");
    const approving = action === "approve";
    const crnNote =
      approving && entry.requested_crn
        ? "\n\nTheir login username changes to the new CRN too."
        : "";

    const confirmed = await confirmAction(
      approving ? `Approve ${entry.full_name}'s correction?` : `Reject ${entry.full_name}'s correction?`,
      approving ? `${summary}${crnNote}` : "Nothing will be changed on their profile.",
      approving ? "Approve" : "Reject"
    );
    if (!confirmed) return;

    setBusyId(entry.id);
    try {
      await (approving ? approveEditRequest(entry.id) : rejectEditRequest(entry.id));
      await load();
      notifySuccess(approving ? "Correction applied" : "Request rejected");
    } catch (err: any) {
      notifyError(
        approving ? "Could not approve" : "Could not reject",
        err?.response?.data?.detail || "Please try again."
      );
      // A stale list is the likely cause (someone else already reviewed it).
      await load();
    } finally {
      setBusyId(null);
    }
  };

  if (!entries && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  const pendingCount = entries?.filter((e) => e.status === "pending").length ?? 0;
  const visible = entries?.filter((e) => filter === "all" || e.status === "pending") ?? [];

  return (
    <AppShell>
      <PageHeader
        eyebrow="Teacher"
        title="Profile Corrections"
        subtitle="Students ask for name, CRN or roll number fixes here. Approving applies the change."
        actions={
        <ButtonGroup>
          <Button variant={filter === "pending" ? "dark" : "outline-secondary"} onClick={() => setFilter("pending")}>
            Pending ({pendingCount})
          </Button>
          <Button variant={filter === "all" ? "dark" : "outline-secondary"} onClick={() => setFilter("all")}>
            All
          </Button>
        </ButtonGroup>
        }
      />
      <p className="d-none">
        Students can't edit their name, CRN or roll number themselves. They request a change and it lands here.
      </p>

      {error && <Alert variant="danger">{error}</Alert>}
      {entries && visible.length === 0 && (
        <p className="text-muted">
          {filter === "pending" ? "No pending requests. You're all caught up." : "No requests yet."}
        </p>
      )}

      <div className="d-flex flex-column gap-3">
        {visible.map((entry) => {
          const isPending = entry.status === "pending";
          return (
            <Card key={entry.id}>
              <Card.Body>
                <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
                  <div>
                    <div className="fw-semibold">{entry.full_name}</div>
                    <div className="text-muted small font-mono">
                      {entry.username}
                      {entry.section && ` · Section ${entry.section}`}
                    </div>
                  </div>
                  <div className="text-end">
                    <span className={`stamp ${STATUS_STAMP[entry.status]}`}>{entry.status}</span>
                    <div className="text-muted small mt-1">{formatDateTime(entry.created_at)}</div>
                  </div>
                </div>

                <div className="d-flex flex-column gap-3">
                  {changesFor(entry).map((change) => (
                    <div className="info-row" key={change.label}>
                      <div className="info-row-label">{change.label}</div>
                      <div className="d-flex align-items-center flex-wrap gap-2">
                        {isPending && (
                          <>
                            <span className="text-muted text-decoration-line-through font-mono">
                              {change.from || "(blank)"}
                            </span>
                            <span aria-hidden="true">→</span>
                          </>
                        )}
                        <span className="fw-semibold font-mono">{change.to}</span>
                      </div>
                    </div>
                  ))}
                  {entry.reason && (
                    <div className="info-row">
                      <div className="info-row-label">Reason</div>
                      <div>{entry.reason}</div>
                    </div>
                  )}
                </div>

                {isPending ? (
                  <div className="d-flex gap-2 mt-3">
                    <Button size="sm" disabled={busyId !== null} onClick={() => review(entry, "approve")}>
                      {busyId === entry.id ? "Working..." : "Approve"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline-danger"
                      disabled={busyId !== null}
                      onClick={() => review(entry, "reject")}
                    >
                      Reject
                    </Button>
                  </div>
                ) : (
                  <div className="text-muted small mt-3">
                    {entry.status === "approved" ? "Approved" : "Rejected"}
                    {entry.reviewed_by_username && ` by ${entry.reviewed_by_username}`}
                    {entry.reviewed_at && ` · ${formatDateTime(entry.reviewed_at)}`}
                  </div>
                )}
              </Card.Body>
            </Card>
          );
        })}
      </div>
    </AppShell>
  );
}
