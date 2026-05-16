from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestVmfLearning(TransactionCase):
    """Cover the Learning Management module: courses, learning paths,
    course assignments, completion, employee learning summary."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Course = cls.env['vmf.course']
        cls.LearningPath = cls.env['vmf.learning.path']
        cls.Assignment = cls.env['vmf.course.assignment']
        cls.Employee = cls.env['hr.employee']
        cls.Skill = cls.env['hr.skill']
        cls.employee = cls.Employee.create({
            'name': 'Learning Test Employee',
            'vmf_employee_category': 'expat_permanent',
        })

    def test_course_creation_and_code_sequence(self):
        course = self.Course.create({
            'name': 'Effective Communication',
            'category': 'behavioral',
            'delivery_mode': 'classroom',
            'duration_hours': 16,
            'cost_per_seat': 250.0,
        })
        self.assertTrue(course.code and course.code.startswith('CRS-'),
            f"Course code should start with CRS-, got {course.code!r}")
        self.assertEqual(course.duration_hours, 16)
        self.assertEqual(course.category, 'behavioral')

    def test_learning_path_aggregates_duration_and_cost(self):
        c1 = self.Course.create({'name': 'C1', 'category': 'technical',
            'duration_hours': 8, 'cost_per_seat': 100.0})
        c2 = self.Course.create({'name': 'C2', 'category': 'technical',
            'duration_hours': 4, 'cost_per_seat': 50.0})
        path = self.LearningPath.create({
            'name': 'New Joiner Path',
            'target_audience': 'new_joiner',
            'course_line_ids': [
                (0, 0, {'course_id': c1.id, 'sequence': 10}),
                (0, 0, {'course_id': c2.id, 'sequence': 20}),
            ],
        })
        self.assertEqual(path.total_duration_hours, 12)
        self.assertEqual(path.total_cost, 150.0)
        self.assertTrue(path.code and path.code.startswith('LP-'))

    def test_course_assignment_lifecycle(self):
        course = self.Course.create({
            'name': 'Safety Induction',
            'category': 'safety',
            'duration_hours': 4,
        })
        target = date.today() + timedelta(days=30)
        assignment = self.Assignment.create({
            'employee_id': self.employee.id,
            'course_id': course.id,
            'target_completion_date': target,
        })
        self.assertEqual(assignment.state, 'assigned')
        self.assertTrue(assignment.name and assignment.name.startswith('CA-'))
        assignment.action_start()
        self.assertEqual(assignment.state, 'in_progress')
        assignment.score = 75.0
        assignment.action_complete()
        self.assertEqual(assignment.state, 'completed')
        self.assertTrue(assignment.is_passed,
            'Score 75 with default pass mark 60 should pass.')
        self.assertTrue(assignment.actual_completion_date,
            'Completion should auto-stamp the actual completion date.')

    def test_course_assignment_fail_when_below_pass_mark(self):
        course = self.Course.create({
            'name': 'Statutory Compliance',
            'category': 'compliance',
            'duration_hours': 2,
        })
        assignment = self.Assignment.create({
            'employee_id': self.employee.id,
            'course_id': course.id,
            'pass_mark': 70,
        })
        assignment.action_start()
        assignment.score = 50.0
        assignment.action_complete()
        self.assertFalse(assignment.is_passed,
            'Score 50 below pass mark 70 must NOT be marked passed.')

    def test_employee_course_summary(self):
        course = self.Course.create({
            'name': 'Leadership Foundations',
            'category': 'leadership',
            'duration_hours': 24,
        })
        a1 = self.Assignment.create({
            'employee_id': self.employee.id,
            'course_id': course.id,
        })
        a2 = self.Assignment.create({
            'employee_id': self.employee.id,
            'course_id': course.id,
        })
        a1.action_start()
        a1.action_complete()
        self.employee.invalidate_recordset(['course_assignment_ids',
            'course_assigned_count', 'course_completed_count', 'course_in_progress_count'])
        self.assertEqual(self.employee.course_assigned_count, 2)
        self.assertEqual(self.employee.course_completed_count, 1)
        self.assertEqual(self.employee.course_in_progress_count, 1)

    def test_course_assignment_cancel_and_reset(self):
        course = self.Course.create({'name': 'Cx', 'category': 'technical', 'duration_hours': 2})
        a = self.Assignment.create({
            'employee_id': self.employee.id,
            'course_id': course.id,
        })
        a.action_cancel()
        self.assertEqual(a.state, 'cancelled')
        a.action_reset()
        self.assertEqual(a.state, 'assigned')
