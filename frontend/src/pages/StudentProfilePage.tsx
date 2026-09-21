import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Card, Table, Form, Button, Alert } from "react-bootstrap";
import Swal from "sweetalert2";
import { notifySuccess, notifyError } from "../utils/alerts";
import {
  getStudentProfile,
  getTodaySchedule,
  getMyEditRequests,
  submitProfileEditRequest,
  uploadProfilePhoto,
  updateEmail,
  updateContactNumber,
  logout,
} from "../api/client";
import type { ScheduleSlot, ProfileEditRequestRecord } from "../api/client";
import AppShell from "../components/AppShell";
import InstallAppButton from "../components/InstallAppButton";
import LoadingScreen from "../components/LoadingScreen";
import PhotoCropModal from "../components/PhotoCropModal";
import { formatTime } from "../utils/time";

type ScanField = "photo" | "email" | "contact_number";

interface Profile {
  full_name: string;
  crn: string;
  urn: string;
  course: string;
  semester: number;
  section: string;
  email: string;
  contact_number: string;
  photo: string | null;
  // What still blocks scanning, and whether that block is switched on. Every
  // profile save returns a fresh copy, so a field's red mark clears the moment
  // it's fixed.
  missing_scan_fields: ScanField[];
  scan_lock_enabled: boolean;
}

const FIELD_LABELS: Record<ScanField, string> = {
  photo: "profile photo",
  email: "email",
  contact_number: "contact number",
};

function joinLabels(fields: ScanField[]): string {
  const labels = fields.map((f) => FIELD_LABELS[f]);
  return labels.length <= 1 ? labels.join("") : `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}`;
}

// A small QR-style mark for the scan card: three finder squares plus data dots.
function QrGlyph() {
  return (
    <svg className="scan-hero-glyph" viewBox="0 0 64 64" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="4">
        <rect x="4" y="4" width="20" height="20" rx="3" />
        <rect x="40" y="4" width="20" height="20" rx="3" />
        <rect x="4" y="40" width="20" height="20" rx="3" />
      </g>
      <g fill="currentColor">
        <rect x="11" y="11" width="6" height="6" />
        <rect x="47" y="11" width="6" height="6" />
        <rect x="11" y="47" width="6" height="6" />
        <rect x="32" y="8" width="5" height="5" />
        <rect x="32" y="20" width="5" height="5" />
        <rect x="32" y="32" width="8" height="8" />
        <rect x="46" y="34" width="5" height="5" />
        <rect x="54" y="42" width="6" height="6" />
        <rect x="42" y="48" width="6" height="6" />
        <rect x="54" y="54" width="6" height="6" />
      </g>
    </svg>
  );
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
  const [photoUploading, setPhotoUploading] = useState(false);
  const [cropSrc, setCropSrc] = useState<string | null>(null);
  const [cropFileName, setCropFileName] = useState("");
  const [editingEmail, setEditingEmail] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [emailSaving, setEmailSaving] = useState(false);
  const [editingContact, setEditingContact] = useState(false);
  const [contactInput, setContactInput] = useState("");
  const [contactSaving, setContactSaving] = useState(false);
  const [showCorrectionForm, setShowCorrectionForm] = useState(false);
  // Session-only snooze — "remind me later" means later this same visit-cycle,
  // not forever, so it reappears next time they actually log in again rather
  // than being silenced permanently by one click.
  const [photoReminderDismissed, setPhotoReminderDismissed] = useState(
    () => sessionStorage.getItem("classpulse_photo_reminder_dismissed") === "1"
  );
  const navigate = useNavigate();
  // Set by the scan screen's "Complete profile" button - they were just told
  // exactly what's missing, so go straight to it instead of stacking another popup.
  const fromScan = Boolean((useLocation().state as { fromScan?: boolean } | null)?.fromScan);

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

  const scrollToProfile = () =>
    document.getElementById("profile-card")?.scrollIntoView({ behavior: "smooth", block: "start" });

  const scrolledFromScanRef = useRef(false);
  useEffect(() => {
    if (!profile || !fromScan || scrolledFromScanRef.current) return;
    scrolledFromScanRef.current = true;
    // Let the cards lay out first, or the scroll lands short.
    setTimeout(scrollToProfile, 150);
  }, [profile, fromScan]);

  const photoPromptShownRef = useRef(false);
  useEffect(() => {
    if (!profile || profile.photo || photoReminderDismissed || fromScan || photoPromptShownRef.current) return;
    photoPromptShownRef.current = true;
    Swal.fire({
      icon: "warning",
      title: "Add a Profile Photo",
      text: "You haven't uploaded a profile photo yet. Add one so your teacher can recognize you when you scan in.",
      confirmButtonText: "Add Photo Now",
      confirmButtonColor: "#9d5fd1",
      showDenyButton: true,
      denyButtonText: "Remind me next time",
    }).then((result) => {
      if (result.isDenied) {
        sessionStorage.setItem("classpulse_photo_reminder_dismissed", "1");
        setPhotoReminderDismissed(true);
      }
    });
  }, [profile, photoReminderDismissed, fromScan]);

  const MAX_SOURCE_PHOTO_BYTES = 15 * 1024 * 1024;

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    // Generous cap just so FileReader doesn't choke on something absurd — the
    // cropper re-encodes to a fixed 512x512 JPEG regardless of source size, so
    // the backend's real 1MB limit is checked against that output, not this.
    if (file.size > MAX_SOURCE_PHOTO_BYTES) {
      notifyError("Image Too Large", "That image is too large to crop. Try a smaller file.");
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
    setPhotoUploading(true);
    try {
      const result = await uploadProfilePhoto(croppedFile);
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              photo: result.photo,
              missing_scan_fields: result.missing_scan_fields,
              scan_lock_enabled: result.scan_lock_enabled,
            }
          : prev
      );
      setCropSrc(null);
      setCropFileName("");
      notifySuccess("Photo Updated", "Your profile photo has been updated.");
    } catch (err: any) {
      const data = err?.response?.data;
      notifyError("Upload Failed", data?.photo?.[0] || "Could not upload photo. Please try again.");
    } finally {
      setPhotoUploading(false);
    }
  };

  const handleStartEditEmail = () => {
    setEmailInput(profile?.email ?? "");
    setEditingEmail(true);
  };

  const handleSaveEmail = async () => {
    setEmailSaving(true);
    try {
      const updated = await updateEmail(emailInput);
      setProfile((prev) =>
        prev ? { ...prev, email: updated.email, missing_scan_fields: updated.missing_scan_fields } : prev
      );
      setEditingEmail(false);
      notifySuccess("Email Updated", "Your email has been updated.");
    } catch (err: any) {
      notifyError("Update Failed", err?.response?.data?.email?.[0] || "Enter a valid email address.");
    } finally {
      setEmailSaving(false);
    }
  };

  const handleStartEditContact = () => {
    setContactInput(profile?.contact_number ?? "");
    setEditingContact(true);
  };

  const handleSaveContact = async () => {
    setContactSaving(true);
    try {
      const updated = await updateContactNumber(contactInput);
      setProfile((prev) =>
        prev
          ? { ...prev, contact_number: updated.contact_number, missing_scan_fields: updated.missing_scan_fields }
          : prev
      );
      setEditingContact(false);
      notifySuccess("Contact Number Updated", "Your contact number has been updated.");
    } catch (err: any) {
      notifyError(
        "Update Failed",
        err?.response?.data?.contact_number?.[0] || "Enter a valid phone number."
      );
    } finally {
      setContactSaving(false);
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
      setShowCorrectionForm(false);
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

  // Red only while it actually blocks scanning (lock on) - with the lock off
  // these fields are just nice-to-have and shouldn't look like errors.
  const blocked = profile.scan_lock_enabled ? profile.missing_scan_fields : [];
  const isMissing = (field: ScanField) => blocked.includes(field);
  const missingClass = (field: ScanField) => (isMissing(field) ? "info-row-missing" : "");

  return (
    <AppShell>
      <div className="mb-3">
        <h1 className="h3 mb-1">Welcome, {profile.full_name}</h1>
        <div className="text-muted small font-mono">
          {profile.crn} · Section {profile.section} · Semester {profile.semester}
        </div>
      </div>

      <div className="scan-hero">
        <div className="scan-hero-body">
          <QrGlyph />
          <div>
            <h2 className="scan-hero-title">Mark your attendance</h2>
            <p className="scan-hero-text">Scan the QR code your teacher is showing on screen.</p>
          </div>
        </div>
        {blocked.length > 0 && (
          <div className="scan-hero-alert" role="alert">
            <span>
              Before you can scan, add your <strong>{joinLabels(blocked)}</strong>.
            </span>
            <button type="button" className="scan-hero-alert-link" onClick={scrollToProfile}>
              Complete profile
            </button>
          </div>
        )}
        <Link to="/student/scan" className="scan-hero-btn">
          Scan Attendance QR
        </Link>
      </div>

      <div className="d-flex flex-wrap gap-4 align-items-start mt-4">
        <Card id="profile-card" style={{ flex: "1 1 420px" }}>
          <Card.Body>
            <div className={`d-flex align-items-center gap-3 mb-3 ${isMissing("photo") ? "photo-block-missing" : ""}`}>
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
                {isMissing("photo") ? (
                  <div className="required-tag mt-1">Profile photo required to scan</div>
                ) : (
                  <div className="text-muted small mt-1">You'll get to crop it next</div>
                )}
              </div>
            </div>

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
              <div className={`info-row ${missingClass("email")}`}>
                <div className="info-row-label">
                  Email {isMissing("email") && <span className="required-tag">Required to scan</span>}
                </div>
                {editingEmail ? (
                  <div>
                    <Form.Control
                      size="sm"
                      type="email"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      autoFocus
                    />
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
                    <span className={`text-break ${isMissing("email") ? "text-muted" : ""}`}>
                      {isMissing("email") ? "Not added yet" : profile.email}
                    </span>
                    <Button
                      size="sm"
                      variant={isMissing("email") ? "danger" : "outline-secondary"}
                      onClick={handleStartEditEmail}
                    >
                      {isMissing("email") ? "Add" : "Edit"}
                    </Button>
                  </div>
                )}
              </div>
              <div className={`info-row ${missingClass("contact_number")}`}>
                <div className="info-row-label">
                  Contact Number {isMissing("contact_number") && <span className="required-tag">Required to scan</span>}
                </div>
                {editingContact ? (
                  <div>
                    <Form.Control
                      size="sm"
                      type="tel"
                      value={contactInput}
                      onChange={(e) => setContactInput(e.target.value)}
                      autoFocus
                    />
                    <div className="d-flex gap-2 mt-2">
                      <Button size="sm" onClick={handleSaveContact} disabled={contactSaving}>
                        {contactSaving ? "Saving..." : "Save"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline-secondary"
                        onClick={() => setEditingContact(false)}
                        disabled={contactSaving}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="d-flex align-items-center gap-2 flex-wrap">
                    <span className={profile.contact_number ? "" : "text-muted"}>
                      {profile.contact_number || "Not added yet"}
                    </span>
                    <Button
                      size="sm"
                      variant={isMissing("contact_number") ? "danger" : "outline-secondary"}
                      onClick={handleStartEditContact}
                    >
                      {profile.contact_number ? "Edit" : "Add"}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </Card.Body>
        </Card>

        {scheduleDay && (
          <Card style={{ flex: "1 1 420px" }}>
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
      </div>

      <Card className="mt-4">
        <Card.Body>
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
            <h2 className="h6 mb-0">Request a Profile Correction</h2>
            {!pendingRequest && !showCorrectionForm && (
              <Button size="sm" variant="outline-secondary" onClick={() => setShowCorrectionForm(true)}>
                Request Correction
              </Button>
            )}
          </div>
          {pendingRequest ? (
            <Alert variant="info" className="mb-0">
              You have a pending request awaiting review
              {pendingRequest.requested_name && <> — name to "{pendingRequest.requested_name}"</>}
              {pendingRequest.requested_crn && <> — CRN to "{pendingRequest.requested_crn}"</>}
              {pendingRequest.requested_urn && <> — roll no. to "{pendingRequest.requested_urn}"</>}.
            </Alert>
          ) : !showCorrectionForm ? (
            <p className="text-muted mb-0 small">
              Need your name, CRN, or roll number fixed? Requesting sends it to the admin for review.
            </p>
          ) : (
            <Form onSubmit={handleEditRequestSubmit}>
              {requestError && <Alert variant="danger" className="py-2">{requestError}</Alert>}
              <div className="d-flex flex-wrap gap-3">
                <Form.Group className="mb-2" style={{ flex: "1 1 220px" }} controlId="requested-name">
                  <Form.Label className="small text-muted mb-1">Correct name</Form.Label>
                  <Form.Control
                    value={requestedName}
                    placeholder={profile.full_name}
                    onChange={(e) => setRequestedName(e.target.value)}
                  />
                </Form.Group>
                <Form.Group className="mb-2" style={{ flex: "1 1 220px" }} controlId="requested-crn">
                  <Form.Label className="small text-muted mb-1">Correct CRN</Form.Label>
                  <Form.Control
                    value={requestedCrn}
                    placeholder={profile.crn}
                    onChange={(e) => setRequestedCrn(e.target.value)}
                  />
                </Form.Group>
                <Form.Group className="mb-2" style={{ flex: "1 1 220px" }} controlId="requested-urn">
                  <Form.Label className="small text-muted mb-1">Correct roll number</Form.Label>
                  <Form.Control
                    value={requestedUrn}
                    placeholder={profile.urn}
                    onChange={(e) => setRequestedUrn(e.target.value)}
                  />
                </Form.Group>
              </div>
              <Form.Group className="mb-3" controlId="request-reason">
                <Form.Label className="small text-muted mb-1">Reason (optional)</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={2}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Form.Group>
              <div className="d-flex gap-2">
                <Button type="submit" size="sm" disabled={requestSubmitting}>
                  {requestSubmitting ? "Submitting..." : "Submit Request"}
                </Button>
                <Button
                  size="sm"
                  variant="outline-secondary"
                  onClick={() => setShowCorrectionForm(false)}
                  disabled={requestSubmitting}
                >
                  Cancel
                </Button>
              </div>
            </Form>
          )}
        </Card.Body>
      </Card>

      <Card className="mt-4">
        <Card.Body className="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <h2 className="h6 mb-0">Account</h2>
          <div className="d-flex gap-2 flex-wrap">
            <Link to="/student/change-password" className="btn btn-outline-secondary btn-sm">
              Change Password
            </Link>
            <InstallAppButton />
          </div>
        </Card.Body>
      </Card>

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
