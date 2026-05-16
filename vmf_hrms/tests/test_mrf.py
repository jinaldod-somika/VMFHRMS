from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestVmfMRF(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.department = self.env['hr.department'].create({
            'name': 'Test Engineering',
            'company_id': self.company.id,
        })
        self.job = self.env['hr.job'].create({
            'name': 'Software Engineer',
            'department_id': self.department.id,
        })
        self.grade = self.env['vmf.grade'].create({
            'name': 'M2_TEST',
            'description': 'Test Manager Grade',
            'grade_level': 'management',
        })
        self.manager = self.env['hr.employee'].create({
            'name': 'Test Manager',
            'company_id': self.company.id,
        })

    def _create_mrf(self, **kwargs):
        vals = {
            'company_id': self.company.id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'grade_id': self.grade.id,
            'requisition_type': 'new_hire',
            'employment_type': 'permanent',
            'employee_category': 'national_permanent',
            'hiring_manager_id': self.manager.id,
            'justification': 'Business need test',
            'budget_currency_id': self.company.currency_id.id,
            'budget_min': 3000,
            'budget_max': 5000,
        }
        vals.update(kwargs)
        return self.env['vmf.mrf'].create(vals)

    def test_mrf_creation_gets_sequence(self):
        mrf = self._create_mrf()
        self.assertNotEqual(mrf.name, 'Draft', 'MRF should have a sequence number')
        self.assertIn('REQ-', mrf.name)

    def test_mrf_approval_workflow(self):
        mrf = self._create_mrf()
        self.assertEqual(mrf.state, 'draft')

        mrf.action_submit()
        self.assertEqual(mrf.state, 'submitted')
        self.assertTrue(mrf.date_submitted)

        mrf.action_dept_approve()
        self.assertEqual(mrf.state, 'dept_approved')

        mrf.action_hr_approve()
        self.assertEqual(mrf.state, 'hr_approved')

        mrf.action_group_hr_approve()
        self.assertEqual(mrf.state, 'group_hr_approved')

        mrf.action_budget_approve()
        self.assertEqual(mrf.state, 'budget_approved')
        self.assertTrue(mrf.date_budget_approved)

    def test_budget_approve_requires_budget(self):
        mrf = self._create_mrf(budget_max=0)
        mrf.action_submit()
        mrf.action_dept_approve()
        mrf.action_hr_approve()
        mrf.action_group_hr_approve()
        with self.assertRaises(UserError):
            mrf.action_budget_approve()

    def test_mrf_hold_log(self):
        mrf = self._create_mrf()
        mrf.action_submit()
        mrf.action_dept_approve()
        mrf.action_hr_approve()
        mrf.action_group_hr_approve()
        mrf.action_budget_approve()
        mrf.action_hold()
        self.assertEqual(mrf.state, 'on_hold')

        # Add hold record
        from datetime import date, timedelta
        hold = self.env['vmf.mrf.hold'].create({
            'mrf_id': mrf.id,
            'hold_start_date': date.today() - timedelta(days=5),
            'hold_end_date': date.today(),
            'hold_reason': 'Budget review',
        })
        self.assertEqual(hold.hold_days, 5)

        mrf.action_reopen()
        self.assertEqual(mrf.state, 'budget_approved')

    def test_mrf_cancel(self):
        mrf = self._create_mrf()
        mrf.action_submit()
        mrf.action_cancel()
        self.assertEqual(mrf.state, 'cancelled')

    def test_position_open_count(self):
        mrf = self._create_mrf(no_of_positions=3)
        self.assertEqual(mrf.open_positions, 3)
        self.assertEqual(mrf.filled_positions, 0)
