from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date


class TestVmfTalent(TransactionCase):
    """Cover the Talent Management module: competency matrix, IDP,
    9-box talent review, succession plan, skill gap."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Competency = cls.env['vmf.competency']
        cls.CompetencyMatrix = cls.env['vmf.competency.matrix']
        cls.IDP = cls.env['vmf.idp']
        cls.IDPAction = cls.env['vmf.idp.action']
        cls.TalentReview = cls.env['vmf.talent.review']
        cls.Succession = cls.env['vmf.succession.plan']
        cls.SuccessorLine = cls.env['vmf.successor.line']
        cls.SkillGap = cls.env['vmf.skill.gap']
        cls.Employee = cls.env['hr.employee']
        cls.Job = cls.env['hr.job']
        cls.Grade = cls.env['vmf.grade']
        cls.Course = cls.env['vmf.course']

        cls.grade_m5 = cls.Grade.create({
            'name': 'TLT-M5', 'description': 'Talent M5', 'grade_level': 'management',
        })
        cls.job_mgr = cls.Job.create({
            'name': 'Mining Operations Manager',
            'grade_id': cls.grade_m5.id,
            'is_critical_role': True,
        })
        cls.emp_incumbent = cls.Employee.create({
            'name': 'John Incumbent', 'job_id': cls.job_mgr.id,
            'vmf_grade_id': cls.grade_m5.id,
        })
        cls.emp_successor = cls.Employee.create({
            'name': 'Jane Successor', 'vmf_grade_id': cls.grade_m5.id,
        })

    # Competency matrix --------------------------------------------------
    def test_competency_matrix_requires_scope(self):
        comp = self.Competency.create({
            'name': 'Project Management', 'category': 'technical',
        })
        with self.assertRaises(ValidationError):
            self.CompetencyMatrix.create({
                'competency_id': comp.id, 'required_level': '3',
            })

    def test_competency_matrix_grade_scope(self):
        comp = self.Competency.create({
            'name': 'Negotiation', 'category': 'behavioral',
        })
        row = self.CompetencyMatrix.create({
            'grade_id': self.grade_m5.id,
            'competency_id': comp.id,
            'required_level': '4',
            'is_critical': True,
        })
        self.assertIn(self.grade_m5.name, row.display_name)
        self.assertIn('Negotiation', row.display_name)

    # IDP ----------------------------------------------------------------
    def test_idp_creation_and_progress(self):
        comp = self.Competency.create({'name': 'Data Analysis', 'category': 'technical'})
        idp = self.IDP.create({
            'employee_id': self.emp_successor.id,
            'period_start': date(2026, 1, 1),
            'period_end': date(2026, 12, 31),
            'aspiration': 'Move into Senior Manager role within 18 months.',
        })
        self.assertTrue(idp.name and idp.name.startswith('IDP-'))
        self.assertEqual(idp.state, 'draft')
        self.assertEqual(idp.overall_progress, 0.0)

        a1 = self.IDPAction.create({
            'idp_id': idp.id,
            'name': 'Take advanced data analysis course',
            'competency_id': comp.id,
            'current_level': '2', 'target_level': '4',
            'action_type': 'course',
        })
        a2 = self.IDPAction.create({
            'idp_id': idp.id,
            'name': 'Mentoring with Group Head',
            'action_type': 'mentoring',
        })
        idp.action_agree()
        self.assertEqual(idp.state, 'agreed')
        idp.action_activate()
        self.assertEqual(idp.state, 'active')

        a1.status = 'completed'
        idp.invalidate_recordset(['overall_progress'])
        self.assertEqual(idp.overall_progress, 50.0,
            'One of two actions complete should give 50%.')

        a2.status = 'completed'
        idp.invalidate_recordset(['overall_progress'])
        self.assertEqual(idp.overall_progress, 100.0)

    def test_idp_action_creates_course_assignment(self):
        comp = self.Competency.create({'name': 'Excel Advanced', 'category': 'technical'})
        course = self.Course.create({'name': 'Excel Advanced Course',
            'category': 'technical', 'duration_hours': 8})
        idp = self.IDP.create({'employee_id': self.emp_successor.id})
        action = self.IDPAction.create({
            'idp_id': idp.id,
            'name': 'Excel training',
            'competency_id': comp.id,
            'action_type': 'course',
            'course_id': course.id,
            'target_date': date(2026, 6, 30),
        })
        action.action_create_course_assignment()
        assignments = self.env['vmf.course.assignment'].search([('idp_action_id', '=', action.id)])
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments.employee_id, self.emp_successor)
        self.assertEqual(assignments.course_id, course)

    # Talent review / 9-box ---------------------------------------------
    def test_nine_box_position_mapping(self):
        # Performance High + Potential High = box 9 (Star)
        review_star = self.TalentReview.create({
            'employee_id': self.emp_successor.id,
            'review_year': 2026,
            'performance_rating': '3',
            'potential_rating': '3',
        })
        self.assertEqual(review_star.nine_box_position, '9')
        self.assertTrue(review_star.is_hipo, 'Box 9 must auto-flag HIPO.')

        # Performance Low + Potential Low = box 1 (Underperformer)
        review_low = self.TalentReview.create({
            'employee_id': self.emp_incumbent.id,
            'review_year': 2026,
            'performance_rating': '1',
            'potential_rating': '1',
        })
        self.assertEqual(review_low.nine_box_position, '1')
        self.assertFalse(review_low.is_hipo)

        # Performance Med + Potential High = box 8 (Growth)
        review_growth = self.TalentReview.create({
            'employee_id': self.emp_successor.id,
            'review_year': 2025,
            'performance_rating': '2',
            'potential_rating': '3',
        })
        self.assertEqual(review_growth.nine_box_position, '8')
        self.assertTrue(review_growth.is_hipo, 'Box 8 must auto-flag HIPO.')

    def test_talent_review_state_transitions(self):
        review = self.TalentReview.create({
            'employee_id': self.emp_successor.id,
            'review_year': 2026,
            'performance_rating': '3',
            'potential_rating': '2',
        })
        self.assertEqual(review.state, 'draft')
        review.action_calibrate()
        self.assertEqual(review.state, 'calibrated')
        review.action_confirm()
        self.assertEqual(review.state, 'confirmed')

    # Succession plan ----------------------------------------------------
    def test_succession_plan_with_successors(self):
        plan = self.Succession.create({
            'critical_role_id': self.job_mgr.id,
            'incumbent_id': self.emp_incumbent.id,
        })
        self.assertEqual(plan.successor_count, 0)
        self.assertEqual(plan.ready_now_count, 0)
        self.assertTrue(plan.is_critical_role,
            'Plan must inherit critical role flag from job position.')

        self.SuccessorLine.create({
            'succession_plan_id': plan.id,
            'candidate_id': self.emp_successor.id,
            'readiness': 'now',
            'sequence': 10,
        })
        plan.invalidate_recordset(['successor_count', 'ready_now_count'])
        self.assertEqual(plan.successor_count, 1)
        self.assertEqual(plan.ready_now_count, 1)

        plan.action_activate()
        self.assertEqual(plan.state, 'active')

    # Skill gap ----------------------------------------------------------
    def test_skill_gap_computation(self):
        comp = self.Competency.create({'name': 'Strategic Planning', 'category': 'leadership'})
        # Required for the M5 grade
        self.CompetencyMatrix.create({
            'grade_id': self.grade_m5.id,
            'competency_id': comp.id,
            'required_level': '5',
            'is_critical': True,
        })
        # Compute gap for incumbent (also at M5)
        self.emp_incumbent.action_compute_skill_gap()
        gaps = self.SkillGap.search([('employee_id', '=', self.emp_incumbent.id)])
        self.assertEqual(len(gaps), 1)
        gap_row = gaps[0]
        self.assertEqual(gap_row.required_level, '5')
        self.assertEqual(gap_row.current_level, '1',
            'Default current level should be 1 (Beginner).')
        self.assertEqual(gap_row.gap, 4, 'Gap should be required(5) - current(1) = 4.')
        self.assertTrue(gap_row.is_critical)

    def test_employee_hipo_flag_from_review(self):
        # Initially not HIPO
        self.emp_successor.invalidate_recordset(['is_hipo'])
        self.assertFalse(self.emp_successor.is_hipo)
        # Create a HIPO review (box 9)
        self.TalentReview.create({
            'employee_id': self.emp_successor.id,
            'review_year': 2026,
            'performance_rating': '3',
            'potential_rating': '3',
        })
        self.emp_successor.invalidate_recordset(['is_hipo', 'talent_review_ids'])
        self.assertTrue(self.emp_successor.is_hipo,
            'Employee must be flagged HIPO after a box-9 talent review.')
