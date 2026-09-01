import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Card, Table, Form, Button, Alert } from "react-bootstrap";
import {
  getStudentProfile,
  getTodaySchedule,
  getMyEditRequests,
  submitProfileEditRequest,
  uploadProfilePhoto,
  updateEmail,
  logout,
} from "../api/client";
import type { ScheduleSlot, ProfileEditRequestRecord } from "../api/client";
import AppShell from "../components/AppShell";
import LoadingScreen from "../components/LoadingScreen";
import PhotoCropModal from "../components/PhotoCropModal";
import { formatTime } from "../utils/time";

interface Profile {
  full_name: string;
  crn: string;
  urn: string;
  course: string;
  semester: number;
  section: string;
  email: string;
  photo: string | null;
}

export default function StudentProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [scheduleDay, setScheduleDay] = useState<string | null>(null);
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
  const [pendingRequest, setPendingRequest] = useState<ProfileEditRequestRecord | null>(null);
  const [requestedName, setRequestedName] = useState("");
  const [requestedCrn, setRequestedCrn] = useState("");
  const [requestedUrn, setRequestedUrn] = useState("");
  const [reason, setReason] = useState("");
  const [requestError, setRequestError] = useState<string | null>(null);
  const [requestSubmitting, setRequestSubmitting] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [cropSrc, setCropSrc] = useState<string | null>(null);
  const [cropFileName, setCropFileName] = useState("");
  const [editingEmail, setEditingEmail] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailSaving, setEmailSaving] = useState(false);
  const navigate = useNavigate();

  const loadEditRequests = () => {
    getMyEditRequests()
      .then((requests) => {
        setPendingRequest(requests.find((r) => r.status === "pending") ?? null);
      })
      .catch(() => {
        // Non-critical — the request form still works, it just won't show a pending banner.
      });
  };

  useEffect(() => {
    getStudentProfile()
      .then(setProfile)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
    getTodaySchedule()
      .then((data) => {
        setScheduleDay(data.day);
        setSlots(data.slots);
      })
      .catch(() => {
        // Timetable card is a convenience — the rest of the dashboard still works without it.
      });
    loadEditRequests();
  }, [navigate]);

  const MAX_SOURCE_PHOTO_BYTES = 15 * 1024 * 1024;

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setPhotoError(null);
    // Generous cap just so FileReader doesn't choke on something absurd — the
    // cropper re-encodes to a fixed 512x512 JPEG regardless of source size, so
    // the backend's real 1MB limit is checked against that output, not this.
    if (file.size > MAX_SOURCE_PHOTO_BYTES) {
      setPhotoError("That image is too large to crop. Try a smaller file.");
      return;
    }
    setCropFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => setCropSrc(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handleCropCancel = () => {
    setCropSrc(null);
    setCropFileName("");
  };

  const handleCropConfirm = async (croppedFile: File) => {
    setPhotoError(null);
    setPhotoUploading(true);
    try {
      const result = await uploadProfilePhoto(croppedFile);
      setProfile((prev) => (prev ? { ...prev, photo: result.photo } : prev));
      setCropSrc(null);
      setCropFileName("");
    } catch (err: any) {
      const data = err?.response?.data;
      setPhotoError(data?.photo?.[0] || "Could not upload photo. Please try again.");
    } finally {
      setPhotoUploading(false);
    }
  };

  const handleStartEditEmail = () => {
    setEmailInput(profile?.email ?? "");
    setEmailError(null);
    setEditingEmail(true);
  };

  const handleSaveEmail = async () => {
    setEmailError(null);
    setEmailSaving(true);
    try {
      const updated = await updateEmail(emailInput);
      setProfile((prev) => (prev ? { ...prev, email: updated.email } : prev));
      setEditingEmail(false);
    } catch (err: any) {
      setEmailError(err?.response?.data?.email?.[0] || "Enter a valid email address.");
    } finally {
      setEmailSaving(false);
    }
  };

  const handleEditRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRequestError(null);
    if (!requestedName && !requestedCrn && !requestedUrn) {
      setRequestError("Enter at least one field you want changed.");
      return;
    }
    setRequestSubmitting(true);
    try {
      await submitProfileEditRequest({
        requested_name: requestedName,
        requested_crn: requestedCrn,
        requested_urn: requestedUrn,
        reason,
      });
      setRequestedName("");
      setRequestedCrn("");
      setRequestedUrn("");
      setReason("");
      loadEditRequests();
    } catch (err: any) {
      setRequestError(err?.response?.data?.detail || "Could not submit the request.");
    } finally {
      setRequestSubmitting(false);
    }
  };

  if (!profile) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="h3 mb-4">Welcome, {profile.full_name}</h1>
      <div className="d-flex gap-2 mb-3 flex-wrap">
        <Link to="/student/scan" className="cta-button">
          Scan Attendance QR
        </Link>
        <Link to="/student/change-password" className="btn btn-outline-secondary">
          Change Password
        </Link>
      </div>
      {!profile.photo && (
        <Alert variant="warning" className="mb-3">
          You haven't uploaded a profile photo yet. Add one below so your teacher can recognize you when you scan
          in.
        </Alert>
      )}
      <Card style={{ maxWidth: 480 }}>
        <Card.Body>
          <div className="d-flex align-items-center gap-3 mb-3">
            {profile.photo ? (
              <img
                src={profile.photo}
                alt="Profile"
                width={72}
                height={72}
                style={{ borderRadius: "12px", objectFit: "cover", border: "2px solid var(--line)" }}
              />
            ) : (
              <span
                className="d-inline-flex align-items-center justify-content-center"
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: "12px",
                  background: "var(--line)",
                  color: "var(--ink-soft)",
                  fontWeight: 700,
                  fontSize: "1.5rem",
                }}
              >
                {(profile.full_name || "?").charAt(0).toUpperCase()}
              </span>
            )}
            <div>
              <label className="btn btn-outline-secondary btn-sm mb-0">
                {photoUploading ? "Uploading..." : profile.photo ? "Change photo" : "Add photo"}
                <input
                  type="file"
                  accept="image/*"
                  hidden
                  disabled={photoUploading}
                  onChange={handlePhotoChange}
                />
              </label>
              <div className="text-muted small mt-1">You'll get to crop it next</div>
            </div>
          </div>
          {photoError && <Alert variant="danger" className="py-2">{photoError}</Alert>}

          <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
            <span className="stamp stamp-neutral">Student ID</span>
            <span className="font-mono text-muted">{profile.crn}</span>
          </div>
          <div className="d-flex flex-column gap-3">
            <div className="info-row">
              <div className="info-row-label">Roll No.</div>
              <div className="font-mono">{profile.urn}</div>
            </div>
            <div className="info-row">
              <div className="info-row-label">Course</div>
              <div>{profile.course}</div>
            </div>
            <div className="info-row">
              <div className="info-row-label">Semester</div>
              <div>{profile.semester}</div>
            </div>
            <div className="info-row">
              <div className="info-row-label">Section</div>
              <div>{profile.section}</div>
            </div>
            <div className="info-row">
              <div className="info-row-label">Email</div>
              {editingEmail ? (
                <div>
                  <Form.Control
                    size="sm"
                    type="email"
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    autoFocus
                  />
                  {emailError && <div className="text-danger small mt-1">{emailError}</div>}
                  <div className="d-flex gap-2 mt-2">
                    <Button size="sm" onClick={handleSaveEmail} disabled={emailSaving}>
                      {emailSaving ? "Saving..." : "Save"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline-secondary"
                      onClick={() => setEditingEmail(false)}
                      disabled={emailSaving}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="d-flex align-items-center gap-2 flex-wrap">
                  <span className="text-break">{profile.email}</span>
                  <Button size="sm" variant="outline-secondary" onClick={handleStartEditEmail}>
                    Edit
                  </Button>
                </div>
              )}
            </div>
          </div>
        </Card.Body>
      </Card>

      <Card className="mt-4" style={{ maxWidth: 480 }}>
        <Card.Body>
          <h2 className="h6 mb-3">Request a Profile Correction</h2>
          {pendingRequest ? (
            <Alert variant="info" className="mb-0">
              You have a pending request awaiting review
              {pendingRequest.requested_name && <> — name to "{pendingRequest.requested_name}"</>}
              {pendingRequest.requested_crn && <> — CRN to "{pendingRequest.requested_crn}"</>}
              {pendingRequest.requested_urn && <> — roll no. to "{pendingRequest.requested_urn}"</>}.
            </Alert>
          ) : (
            <Form onSubmit={handleEditRequestSubmit}>
              {requestError && <Alert variant="danger" className="py-2">{requestError}</Alert>}
              <Form.Group className="mb-2" controlId="requested-name">
                <Form.Label className="small text-muted mb-1">Correct name</Form.Label>
                <Form.Control
                  value={requestedName}
                  placeholder={profile.full_name}
                  onChange={(e) => setRequestedName(e.target.value)}
                />
              </Form.Group>
              <Form.Group className="mb-2" controlId="requested-crn">
                <Form.Label className="small text-muted mb-1">Correct CRN</Form.Label>
                <Form.Control
                  value={requestedCrn}
                  placeholder={profile.crn}
                  onChange={(e) => setRequestedCrn(e.target.value)}
                />
              </Form.Group>
              <Form.Group className="mb-2" controlId="requested-urn">
                <Form.Label className="small text-muted mb-1">Correct roll number</Form.Label>
                <Form.Control
                  value={requestedUrn}
                  placeholder={profile.urn}
                  onChange={(e) => setRequestedUrn(e.target.value)}
                />
              </Form.Group>
              <Form.Group className="mb-3" controlId="request-reason">
                <Form.Label className="small text-muted mb-1">Reason (optional)</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={2}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Form.Group>
              <Button type="submit" size="sm" disabled={requestSubmitting}>
                {requestSubmitting ? "Submitting..." : "Submit Request"}
              </Button>
            </Form>
          )}
        </Card.Body>
      </Card>

      {scheduleDay && (
        <Card className="mt-4" style={{ maxWidth: 480 }}>
          <Card.Body>
            <h2 className="h6 mb-3">{scheduleDay}'s Timetable — Section {profile.section}</h2>
            {(() => {
              const mySlots = slots.filter((slot) => slot.section === profile.section);
              return mySlots.length === 0 ? (
                <p className="text-muted mb-0">No training sessions scheduled today.</p>
              ) : (
                <div className="table-responsive">
                  <Table size="sm" borderless className="mb-0">
                    <tbody>
                      {mySlots.map((slot, index) => (
                        <tr key={index}>
                          <td className="text-muted font-mono">
                            {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                          </td>
                          <td>{slot.subject}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              );
            })()}
          </Card.Body>
        </Card>
      )}
      <PhotoCropModal
        show={!!cropSrc}
        imageSrc={cropSrc}
        fileName={cropFileName}
        onCancel={handleCropCancel}
        onConfirm={handleCropConfirm}
        confirming={photoUploading}
      />
    </AppShell>
  );
}
