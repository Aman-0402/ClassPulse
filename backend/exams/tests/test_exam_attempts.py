from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import StudentProfile
from exams.models import Exam, ExamAttempt, MCQQuestion, PracticalQuestion

User = get_user_model()


class ExamAttemptTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(
            username="s1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Sam"
        )
        StudentProfile.objects.create(user=self.student, crn="s1", urn="u1", course="BBA", semester=3, section="A")

        self.mcqs = [
            MCQQuestion.objects.create(
                text=f"Q{i}", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="a"
            )
            for i in range(7)
        ]
        easy = PracticalQuestion.objects.create(text="Easy Q", difficulty="easy")
        hard = PracticalQuestion.objects.create(text="Hard Q", difficulty="hard")
        now = timezone.now()
        self.exam = Exam.objects.create(
            title="Midterm",
            section="A",
            easy_practical=easy,
            hard_practical=hard,
            start_time=now - timezone.timedelta(minutes=5),
            end_time=now + timezone.timedelta(hours=1),
        )
        self.attempt_url = reverse("student-exam-attempt", args=[self.exam.id])
        self.submit_url = reverse("student-exam-submit", args=[self.exam.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.student).key}")

    def test_first_open_assigns_five_random_mcqs_no_answers_exposed(self):
        response = self.client.get(self.attempt_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["mcqs"]), 5)
        self.assertNotIn("correct_option", response.data["mcqs"][0])
        self.assertEqual(response.data["easy_practical_text"], "Easy Q")
        self.assertEqual(response.data["hard_practical_text"], "Hard Q")
        self.assertFalse(response.data["submitted"])

    def test_reopening_resumes_same_questions(self):
        first = self.client.get(self.attempt_url).data
        second = self.client.get(self.attempt_url).data
        self.assertEqual([q["id"] for q in first["mcqs"]], [q["id"] for q in second["mcqs"]])
        self.assertEqual(ExamAttempt.objects.filter(exam=self.exam, student=self.student).count(), 1)

    def test_cannot_start_when_exam_not_open(self):
        self.exam.manual_status = Exam.STATUS_FORCED_CLOSED
        self.exam.save()
        self.assertEqual(self.client.get(self.attempt_url).status_code, 403)

    def test_wrong_section_student_blocked(self):
        other = User.objects.create_user(username="s2", password="pw12345678", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=other, crn="s2", urn="u2", course="BBA", semester=3, section="B")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=other).key}")
        self.assertEqual(self.client.get(self.attempt_url).status_code, 403)

    def test_answer_and_submit_scores_correctly(self):
        started = self.client.get(self.attempt_url).data
        qids = [q["id"] for q in started["mcqs"]]
        # 3 correct (option "a"), 2 wrong
        answers = {str(qids[0]): "a", str(qids[1]): "a", str(qids[2]): "a", str(qids[3]): "b", str(qids[4]): "c"}
        patched = self.client.patch(self.attempt_url, {"answers": answers}, format="json")
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["answers"], answers)

        submitted = self.client.post(self.submit_url)
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data["score"], 3)
        self.assertEqual(submitted.data["total"], 5)
        self.assertTrue(submitted.data["submitted"])

    def test_cannot_answer_after_submit(self):
        started = self.client.get(self.attempt_url).data
        qid = started["mcqs"][0]["id"]
        self.client.post(self.submit_url)
        response = self.client.patch(self.attempt_url, {"answers": {str(qid): "a"}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_resubmit_is_idempotent(self):
        self.client.get(self.attempt_url)
        first = self.client.post(self.submit_url).data
        second = self.client.post(self.submit_url).data
        self.assertEqual(first["score"], second["score"])

    def test_invalid_option_letter_rejected(self):
        started = self.client.get(self.attempt_url).data
        qid = started["mcqs"][0]["id"]
        response = self.client.patch(self.attempt_url, {"answers": {str(qid): "z"}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_answering_a_question_not_in_attempt_rejected(self):
        self.client.get(self.attempt_url)
        foreign = MCQQuestion.objects.create(
            text="Other", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="a"
        )
        response = self.client.patch(self.attempt_url, {"answers": {str(foreign.id): "a"}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cannot_answer_after_window_closes(self):
        self.client.get(self.attempt_url)
        self.exam.manual_status = Exam.STATUS_FORCED_CLOSED
        self.exam.save()
        response = self.client.patch(self.attempt_url, {"answers": {}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_student_exam_list_shows_status_and_score(self):
        list_url = reverse("student-exam-list")
        self.assertEqual(self.client.get(list_url).data[0]["status"], "not_started")
        self.client.get(self.attempt_url)
        self.assertEqual(self.client.get(list_url).data[0]["status"], "in_progress")
        self.client.post(self.submit_url)
        entry = self.client.get(list_url).data[0]
        self.assertEqual(entry["status"], "submitted")
        self.assertIsNotNone(entry["score"])

    def test_teacher_can_see_results(self):
        started = self.client.get(self.attempt_url).data
        qids = [q["id"] for q in started["mcqs"]]
        self.client.patch(self.attempt_url, {"answers": {str(qids[0]): "a"}}, format="json")
        self.client.post(self.submit_url)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        response = self.client.get(reverse("exam-results", args=[self.exam.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["submitted"], 1)
        self.assertEqual(response.data["students"][0]["crn"], "s1")
        self.assertEqual(response.data["students"][0]["score"], 1)
        self.assertEqual(response.data["average_score"], 1.0)

    def test_students_cannot_see_results(self):
        response = self.client.get(reverse("exam-results", args=[self.exam.id]))
        self.assertEqual(response.status_code, 403)
