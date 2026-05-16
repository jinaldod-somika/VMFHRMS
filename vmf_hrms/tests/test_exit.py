from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestVmfExit(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Exit Employee',
            'company_id': self.company.id,
        })

    def test_exit_request_creation(self):
        exit_req = self.env['vmf.exit.request'].create({
            'employee_id': self.employee.id,
            'exit_type': 'resignation',
            'resignation_date': date.today(),
            'last_working_date': date.today() + timedelta(days=30),
            'notice_period_days': 30,
        })
        self.assertNotEqual(exit_req.name, 'New')
        self.assertIn('EXIT-', exit_req.name)

    def test_notice_period_calculation(self):
        exit_req = self.env['vmf.exit.request'].create({
            'employee_id': self.employee.id,
            'exit_type': 'resignation',
            'resignation_date': date.today(),
            'last_working_date': date.today() + timedelta(days=20),
            'notice_period_days': 30,
        })
        self.assertEqual(exit_req.notice_served_days, 20)
        self.assertEqual(exit_req.notice_shortfall_days, 10)

    def test_clearance_items_created_on_submit(self):
        exit_req = self.env['vmf.exit.request'].create({
            'employee_id': self.employee.id,
            'exit_type': 'resignation',
            'resignation_date': date.today(),
            'last_working_date': date.today() + timedelta(days=30),
        })
        exit_req.action_submit()
        self.assertTrue(exit_req.clearance_ids)
        departments = exit_req.clearance_ids.mapped('department_name')
        self.assertIn('IT', departments)
        self.assertIn('Finance', departments)
        self.assertIn('HR', departments)

    def test_clearance_complete_flag(self):
        exit_req = self.env['vmf.exit.request'].create({
            'employee_id': self.employee.id,
            'exit_type': 'resignation',
            'resignation_date': date.today(),
            'last_working_date': date.today() + timedelta(days=30),
        })
        exit_req.action_submit()
        self.assertFalse(exit_req.clearance_complete)

        # Clear all items
        for item in exit_req.clearance_ids:
            item.action_clear()

        exit_req._compute_clearance_complete()
        self.assertTrue(exit_req.clearance_complete)

    def test_ff_settlement_creation(self):
        grade = self.env['vmf.grade'].create({
            'name': 'M1_EXIT',
            'description': 'Exit Test Grade',
            'grade_level': 'management',
        })
        structure = self.env['vmf.salary.structure'].create({
            'name': 'Exit Test Structure',
            'code': 'EXIT_TEST',
            'currency_id': self.company.currency_id.id,
        })
        contract = self.env['vmf.employee.contract'].create({
            'name': 'Exit Test Contract',
            'employee_id': self.employee.id,
            'date_start': date(2024, 1, 1),
            'structure_id': structure.id,
            'basic_salary': 3000,
            'state': 'active',
        })
        exit_req = self.env['vmf.exit.request'].create({
            'employee_id': self.employee.id,
            'exit_type': 'resignation',
            'resignation_date': date.today(),
            'last_working_date': date.today() + timedelta(days=30),
            'state': 'hr_processing',
        })
        exit_req.action_compute_ff()
        self.assertTrue(exit_req.ff_settlement_id)
        self.assertNotEqual(exit_req.ff_settlement_id.name, 'New')
