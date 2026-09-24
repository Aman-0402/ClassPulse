import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Swal from "sweetalert2";
import { Alert, Button, Form, Modal } from "react-bootstrap";
import {
  bulkUploadMCQs,
  deleteMCQQuestion,
  deletePracticalQuestion,
  getMCQQuestions,
  getPracticalQuestions,
  logout,
  saveMCQQuestion,
  savePracticalQuestion,
} from "../../api/client";
import type { MCQQuestion, MCQQuestionInput, PracticalQuestion, PracticalQuestionInput } from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingScreen from "../../components/LoadingScreen";
import PageHeader from "../../components/PageHeader";
import { confirmAction, notifyError, notifySuccess } from "../../utils/alerts";

const EMPTY_MCQ: MCQQuestionInput = {
  text: "",
  option_a: "",
  option_b: "",
  option_c: "",
  option_d: "",
  correct_option: "a",
  is_active: true,
};
const EMPTY_PRACTICAL: PracticalQuestionInput = { text: "", difficulty: "easy", is_active: true };

function firstError(data: any): string {
  if (!data) return "Could not save this question.";
  if (typeof data.detail === "string") return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? String(first[0]) : String(first ?? "Could not save this question.");
}

export default function QuestionBankPage() {
  const [tab, setTab] = useState<"mcq" | "practical">("mcq");
  const [mcqs, setMcqs] = useState<MCQQuestion[] | null>(null);
  const [practicals, setPracticals] = useState<PracticalQuestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [editingMcq, setEditingMcq] = useState<MCQQuestion | "new" | null>(null);
  const [mcqForm, setMcqForm] = useState<MCQQuestionInput>(EMPTY_MCQ);
  const [mcqFormError, setMcqFormError] = useState<string | null>(null);
  const [savingMcq, setSavingMcq] = useState(false);

  const [editingPractical, setEditingPractical] = useState<PracticalQuestion | "new" | null>(null);
  const [practicalForm, setPracticalForm] = useState<PracticalQuestionInput>(EMPTY_PRACTICAL);
  const [practicalFormError, setPracticalFormError] = useState<string | null>(null);
  const [savingPractical, setSavingPractical] = useState(false);

  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const navigate = useNavigate();

  const loadAll = () => {
    Promise.all([getMCQQuestions(), getPracticalQuestions()])
      .then(([mcqResult, practicalResult]) => {
        setMcqs(mcqResult);
        setPracticals(practicalResult);
        setError(null);
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          logout();
          navigate("/login", { replace: true });
        } else {
          setError("Could not load the question bank.");
        }
      });
  };

  useEffect(loadAll, [navigate]);

  const openNewMcq = () => {
    setMcqForm(EMPTY_MCQ);
    setMcqFormError(null);
    setEditingMcq("new");
  };

  const openEditMcq = (q: MCQQuestion) => {
    setMcqForm({
      text: q.text,
      option_a: q.option_a,
      option_b: q.option_b,
      option_c: q.option_c,
      option_d: q.option_d,
      correct_option: q.correct_option,
      is_active: q.is_active,
    });
    setMcqFormError(null);
    setEditingMcq(q);
  };

  const handleSaveMcq = async (e: React.FormEvent) => {
    e.preventDefault();
    setMcqFormError(null);
    setSavingMcq(true);
    try {
      await saveMCQQuestion(mcqForm, editingMcq !== "new" && editingMcq ? editingMcq.id : undefined);
      setEditingMcq(null);
      loadAll();
      notifySuccess("Saved", "The MCQ has been saved to the bank.");
    } catch (err: any) {
      setMcqFormError(firstError(err?.response?.data));
    } finally {
      setSavingMcq(false);
    }
  };

  const handleToggleMcqActive = async (q: MCQQuestion) => {
    try {
      await saveMCQQuestion({ ...q, is_active: !q.is_active }, q.id);
      loadAll();
    } catch {
      notifyError("Update Failed", "Could not change this question's status.");
    }
  };

  const handleDeleteMcq = async (q: MCQQuestion) => {
    const ok = await confirmAction("Delete this question?", q.text, "Delete");
    if (!ok) return;
    try {
      await deleteMCQQuestion(q.id);
      loadAll();
    } catch {
      notifyError("Delete Failed", "Could not delete that question.");
    }
  };

  const handleCsvChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      const result = await bulkUploadMCQs(file);
      loadAll();
      if (result.errors.length === 0) {
        notifySuccess("Questions Uploaded", `${result.created} MCQ(s) added to the bank.`);
      } else {
        Swal.fire({
          icon: result.created > 0 ? "warning" : "error",
          title: result.created > 0 ? "Uploaded With Some Rows Skipped" : "Upload Failed",
          html: `<p>${result.created} question(s) added. ${result.errors.length} row(s) skipped:</p>
                 <ul style="text-align:left;max-height:220px;overflow:auto;padding-left:1.2em">
                   ${result.errors.map((e) => `<li>${e}</li>`).join("")}
                 </ul>`,
          confirmButtonColor: "#9d5fd1",
        });
      }
    } catch (err: any) {
      notifyError("Upload Failed", err?.response?.data?.detail || "Could not read that CSV file.");
    } finally {
      setUploading(false);
    }
  };

  const openNewPractical = () => {
    setPracticalForm(EMPTY_PRACTICAL);
    setPracticalFormError(null);
    setEditingPractical("new");
  };

  const openEditPractical = (q: PracticalQuestion) => {
    setPracticalForm({ text: q.text, difficulty: q.difficulty, is_active: q.is_active });
    setPracticalFormError(null);
    setEditingPractical(q);
  };

  const handleSavePractical = async (e: React.FormEvent) => {
    e.preventDefault();
    setPracticalFormError(null);
    setSavingPractical(true);
    try {
      await savePracticalQuestion(
        practicalForm,
        editingPractical !== "new" && editingPractical ? editingPractical.id : undefined
      );
      setEditingPractical(null);
      loadAll();
      notifySuccess("Saved", "The practical question has been saved to the bank.");
    } catch (err: any) {
      setPracticalFormError(firstError(err?.response?.data));
    } finally {
      setSavingPractical(false);
    }
  };

  const handleTogglePracticalActive = async (q: PracticalQuestion) => {
    try {
      await savePracticalQuestion({ ...q, is_active: !q.is_active }, q.id);
      loadAll();
    } catch {
      notifyError("Update Failed", "Could not change this question's status.");
    }
  };

  const handleDeletePractical = async (q: PracticalQuestion) => {
    const ok = await confirmAction("Delete this question?", q.text, "Delete");
    if (!ok) return;
    try {
      await deletePracticalQuestion(q.id);
      loadAll();
    } catch {
      notifyError("Delete Failed", "Could not delete that question.");
    }
  };

  if (!mcqs && !practicals && !error) {
    return (
      <AppShell>
        <LoadingScreen />
      </AppShell>
    );
  }

  const activeMcqCount = (mcqs ?? []).filter((q) => q.is_active).length;
  const activeEasyCount = (practicals ?? []).filter((q) => q.is_active && q.difficulty === "easy").length;
  const activeHardCount = (practicals ?? []).filter((q) => q.is_active && q.difficulty === "hard").length;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin"
        title="Question Bank"
        subtitle="Build the pool exams draw from. Each student gets 5 random active MCQs; you pick 1 easy + 1 hard practical per exam."
        actions={
          <div className="d-flex gap-2 flex-wrap">
            {tab === "mcq" && (
              <>
                <Button
                  variant="outline-secondary"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? "Uploading..." : "Upload CSV"}
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  hidden
                  onChange={handleCsvChange}
                />
              </>
            )}
            <Button onClick={tab === "mcq" ? openNewMcq : openNewPractical}>
              + Add {tab === "mcq" ? "MCQ" : "practical question"}
            </Button>
          </div>
        }
      />
      {tab === "mcq" && (
        <p className="text-muted small mb-3">
          CSV columns (any order, header required): <code>text, option_a, option_b, option_c, option_d, correct_option</code>{" "}
          — correct_option is a/b/c/d.
        </p>
      )}

      {error && <Alert variant="danger">{error}</Alert>}

      <div className="sa-segment mb-4" style={{ maxWidth: 420 }} role="tablist">
        <button type="button" role="tab" aria-checked={tab === "mcq"} className={tab === "mcq" ? "sa-segment-on" : ""} onClick={() => setTab("mcq")}>
          MCQs ({activeMcqCount} active)
        </button>
        <button type="button" role="tab" aria-checked={tab === "practical"} className={tab === "practical" ? "sa-segment-on" : ""} onClick={() => setTab("practical")}>
          Practicals ({activeEasyCount} easy · {activeHardCount} hard)
        </button>
      </div>

      {tab === "mcq" ? (
        (mcqs ?? []).length === 0 ? (
          <div className="empty-state">No MCQs yet. Add at least 5 active ones before scheduling an exam.</div>
        ) : (
          <div className="tk-list">
            {(mcqs ?? []).map((q) => (
              <div key={q.id} className={`tk-card ${q.is_active ? "" : "qb-inactive"}`}>
                <div className="tk-card-head">
                  <h3 className="tk-title">{q.text}</h3>
                  <span className="stamp stamp-neutral">Answer: {q.correct_option.toUpperCase()}</span>
                </div>
                <ul className="qb-options">
                  {(["a", "b", "c", "d"] as const).map((letter) => (
                    <li key={letter} className={letter === q.correct_option ? "qb-correct" : ""}>
                      {letter.toUpperCase()}. {q[`option_${letter}`]}
                    </li>
                  ))}
                </ul>
                <div className="tk-meta">
                  <span>{q.is_active ? "Active" : "Retired — not used in new exams"}</span>
                  <div className="tk-actions">
                    <button type="button" onClick={() => handleToggleMcqActive(q)}>
                      {q.is_active ? "Retire" : "Reactivate"}
                    </button>
                    <button type="button" onClick={() => openEditMcq(q)}>
                      Edit
                    </button>
                    <button type="button" className="tt-danger" onClick={() => handleDeleteMcq(q)}>
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (practicals ?? []).length === 0 ? (
        <div className="empty-state">No practical questions yet. Add at least one easy and one hard.</div>
      ) : (
        <div className="tk-list">
          {(practicals ?? []).map((q) => (
            <div key={q.id} className={`tk-card ${q.is_active ? "" : "qb-inactive"}`}>
              <div className="tk-card-head">
                <h3 className="tk-title">{q.text}</h3>
                <span className={`stamp ${q.difficulty === "hard" ? "stamp-absent" : "stamp-present"}`}>
                  {q.difficulty}
                </span>
              </div>
              <div className="tk-meta">
                <span>{q.is_active ? "Active" : "Retired — not used in new exams"}</span>
                <div className="tk-actions">
                  <button type="button" onClick={() => handleTogglePracticalActive(q)}>
                    {q.is_active ? "Retire" : "Reactivate"}
                  </button>
                  <button type="button" onClick={() => openEditPractical(q)}>
                    Edit
                  </button>
                  <button type="button" className="tt-danger" onClick={() => handleDeletePractical(q)}>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal show={editingMcq !== null} onHide={() => setEditingMcq(null)} centered size="lg">
        <Form onSubmit={handleSaveMcq}>
          <Modal.Header closeButton>
            <Modal.Title className="h5">{editingMcq === "new" ? "Add MCQ" : "Edit MCQ"}</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {mcqFormError && <Alert variant="danger">{mcqFormError}</Alert>}
            <Form.Group className="mb-3" controlId="mcq-text">
              <Form.Label>Question</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={mcqForm.text}
                onChange={(e) => setMcqForm({ ...mcqForm, text: e.target.value })}
                required
              />
            </Form.Group>
            {(["a", "b", "c", "d"] as const).map((letter) => (
              <Form.Group className="mb-2" controlId={`mcq-option-${letter}`} key={letter}>
                <Form.Label>Option {letter.toUpperCase()}</Form.Label>
                <div className="d-flex gap-2 align-items-center">
                  <Form.Check
                    type="radio"
                    name="correct_option"
                    checked={mcqForm.correct_option === letter}
                    onChange={() => setMcqForm({ ...mcqForm, correct_option: letter })}
                    title="Correct answer"
                  />
                  <Form.Control
                    value={mcqForm[`option_${letter}`]}
                    onChange={(e) => setMcqForm({ ...mcqForm, [`option_${letter}`]: e.target.value })}
                    maxLength={500}
                    required
                  />
                </div>
              </Form.Group>
            ))}
            <Form.Text className="text-muted">Select the radio next to the correct option.</Form.Text>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="outline-secondary" onClick={() => setEditingMcq(null)} disabled={savingMcq}>
              Cancel
            </Button>
            <Button type="submit" disabled={savingMcq}>
              {savingMcq ? "Saving..." : "Save"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <Modal show={editingPractical !== null} onHide={() => setEditingPractical(null)} centered>
        <Form onSubmit={handleSavePractical}>
          <Modal.Header closeButton>
            <Modal.Title className="h5">{editingPractical === "new" ? "Add practical question" : "Edit practical question"}</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {practicalFormError && <Alert variant="danger">{practicalFormError}</Alert>}
            <Form.Group className="mb-3" controlId="practical-text">
              <Form.Label>Question</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={practicalForm.text}
                onChange={(e) => setPracticalForm({ ...practicalForm, text: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group controlId="practical-difficulty">
              <Form.Label>Difficulty</Form.Label>
              <Form.Select
                value={practicalForm.difficulty}
                onChange={(e) => setPracticalForm({ ...practicalForm, difficulty: e.target.value as "easy" | "hard" })}
              >
                <option value="easy">Easy</option>
                <option value="hard">Hard</option>
              </Form.Select>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="outline-secondary" onClick={() => setEditingPractical(null)} disabled={savingPractical}>
              Cancel
            </Button>
            <Button type="submit" disabled={savingPractical}>
              {savingPractical ? "Saving..." : "Save"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </AppShell>
  );
}
