from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestVmfCandidate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.department = self.env['hr.department'].create({
            'name': 'Test HR Dept',
            'company_id': self.company.id,
        })
        self.job = self.env['hr.job'].create({
            'name': 'HR Manager',
            'department_id': self.department.id,
        })
        self.grade = self.env['vmf.grade'].create({
            'name': 'M3_CAND',
            'description': 'Test Grade for Candidate',
            'grade_level': 'management',
        })
        self.manager_emp = self.env['hr.employee'].create({
            'name': 'Hiring Manager Cand',
            'company_id': self.company.id,
        })
        self.mrf = self.env['vmf.mrf'].create({
            'company_id': self.company.id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'grade_id': self.grade.id,
            'requisition_type': 'new_hire',
            'employment_type': 'permanent',
            'employee_category': 'national_permanent',
            'hiring_manager_id': self.manager_emp.id,
            'justification': 'Need HR Manager',
            'budget_currency_id': self.company.currency_id.id,
            'budget_max': 5000,
            'state': 'budget_approved',
        })

    def _create_candidate(self, **kwargs):
        vals = {
            'candidate_name': 'Test Candidate',
            'email': 'test.candidate@example.com',
            'mobile': '+1234567890',
            'mrf_id': self.mrf.id,
            'sourcing_channel': 'linkedin',
            'resume_received_date': date.today() - timedelta(days=15),
        }
        vals.update(kwargs)
        return self.env['vmf.candidate'].create(vals)

    def test_candidate_creation_gets_uid(self):
        cand = self._create_candidate()
        self.assertNotEqual(cand.name, 'New')
        self.assertIn('CAND-', cand.name)

    def test_candidate_pipeline_flow(self):
        cand = self._create_candidate()
        self.assertEqual(cand.state, 'new')

        cand.action_move_to_screening()
        self.assertEqual(cand.state, 'screening')

        cand.action_schedule_interview1()
        self.assertEqual(cand.state, 'interview_1')
        cand.write({'interview1_result': 'cleared', 'interview1_date': date.today()})

        cand.action_schedule_interview2()
        self.assertEqual(cand.state, 'interview_2')

        cand.action_select()
        self.assertEqual(cand.state, 'selected')

        cand.action_prepare_offer()
        self.assertEqual(cand.state, 'offer_prepared')
        self.assertTrue(cand.offer_prepared_date)

        cand.action_release_offer()
        self.assertEqual(cand.state, 'offer_released')

        cand.action_accept_offer()
        self.assertEqual(cand.state, 'offer_accepted')

        cand.action_bgv()
        self.assertEqual(cand.state, 'bgv')

        cand.action_confirm_joining()
        self.assertEqual(cand.state, 'joining_confirmed')

        cand.action_mark_joined()
        self.assertEqual(cand.state, 'joined')

    def test_offer_drop_log(self):
        cand = self._create_candidate()
        cand.action_move_to_screening()
        cand.action_schedule_interview1()
        cand.action_select()
        cand.action_prepare_offer()
        cand.action_release_offer()

        # Record a drop
        drop = self.env['vmf.candidate.drop'].create({
            'candidate_id': cand.id,
            'drop_date': date.today(),
            'drop_stage': 'after_ol',
            'drop_reason': 'Accepted competing offer',
        })

        self.assertTrue(cand.is_dropped)
        self.assertGreater(drop.days_lost, 0)

    def test_candidate_hold(self):
        cand = self._create_candidate()
        hold = self.env['vmf.candidate.hold'].create({
            'candidate_id': cand.id,
            'hold_start': date.today() - timedelta(days=10),
            'hold_end': date.today(),
            'hold_reason': 'Business hiring freeze',
        })
        self.assertEqual(hold.hold_days, 10)

    def test_tat_calculation(self):
        start_date = date.today() - timedelta(days=30)
        cand = self._create_candidate(resume_received_date=start_date)
        # TAT should be at least 30 days
        self.assertGreaterEqual(cand.tat_days, 30)

    def test_create_employee_from_candidate(self):
        cand = self._create_candidate()
        # Move to joined state
        cand.write({'state': 'joined'})
        result = cand.action_create_employee()
        self.assertTrue(cand.employee_id)
        self.assertEqual(cand.employee_id.name, cand.candidate_name)
        self.assertEqual(result['res_model'], 'hr.employee')
