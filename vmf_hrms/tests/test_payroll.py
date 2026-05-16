from odoo.tests.common import TransactionCase
from datetime import date
import calendar


class TestVmfPayroll(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.department = self.env['hr.department'].create({
            'name': 'Test Payroll Dept',
            'company_id': self.company.id,
        })
        self.grade = self.env['vmf.grade'].create({
            'name': 'M2_PAY',
            'description': 'Test Payroll Grade',
            'grade_level': 'management',
        })
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Payroll Employee',
            'company_id': self.company.id,
            'department_id': self.department.id,
            'vmf_employee_category': 'expat_permanent',
            'vmf_grade_id': self.grade.id,
        })
        # Create salary structure
        self.structure = self.env['vmf.salary.structure'].create({
            'name': 'Expat Structure Test',
            'code': 'EXPAT_TEST',
            'company_id': self.company.id,
            'currency_id': self.company.currency_id.id,
        })
        # Add rules
        self.env['vmf.salary.rule'].create([
            {
                'structure_id': self.structure.id,
                'sequence': 10,
                'name': 'Basic Pay',
                'code': 'BASIC',
                'component_type': 'earning',
                'computation': 'fixed',
                'amount': 0,  # Will be taken from contract
                'appears_on_payslip': True,
            },
            {
                'structure_id': self.structure.id,
                'sequence': 20,
                'name': 'HRA',
                'code': 'HRA',
                'component_type': 'earning',
                'computation': 'percent_basic',
                'amount': 40,
                'appears_on_payslip': True,
            },
            {
                'structure_id': self.structure.id,
                'sequence': 30,
                'name': 'Transport Allowance',
                'code': 'TA',
                'component_type': 'earning',
                'computation': 'fixed',
                'amount': 200,
                'appears_on_payslip': True,
            },
            {
                'structure_id': self.structure.id,
                'sequence': 40,
                'name': 'PF Employee',
                'code': 'PF_EMP',
                'component_type': 'deduction',
                'computation': 'percent_basic',
                'amount': 12,
                'appears_on_payslip': True,
            },
        ])
        # Create contract
        self.contract = self.env['vmf.employee.contract'].create({
            'name': 'Test Contract',
            'employee_id': self.employee.id,
            'date_start': date(2025, 1, 1),
            'structure_id': self.structure.id,
            'basic_salary': 5000,
            'state': 'active',
        })

    def test_salary_structure_creation(self):
        self.assertEqual(len(self.structure.line_ids), 4)

    def test_payroll_run_creation(self):
        run = self.env['vmf.payroll.run'].create({
            'company_id': self.company.id,
            'date_start': date(2026, 3, 1),
            'date_end': date(2026, 3, 31),
        })
        self.assertNotEqual(run.name, 'New')
        self.assertEqual(run.state, 'draft')

    def test_payslip_compute(self):
        run = self.env['vmf.payroll.run'].create({
            'company_id': self.company.id,
            'date_start': date(2026, 3, 1),
            'date_end': date(2026, 3, 31),
        })
        slip = self.env['vmf.payslip'].create({
            'payroll_run_id': run.id,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_start': date(2026, 3, 1),
            'date_end': date(2026, 3, 31),
        })
        slip.action_compute()
        self.assertEqual(slip.state, 'computed')
        self.assertGreater(slip.working_days, 0)
        self.assertGreater(slip.gross_pay, 0)

    def test_contract_gross_calculation(self):
        contract = self.contract
        contract.write({
            'basic_salary': 5000,
            'hra': 2000,
            'transport_allowance': 500,
        })
        self.assertEqual(contract.gross_salary, 7500)

    def test_payroll_run_workflow(self):
        run = self.env['vmf.payroll.run'].create({
            'company_id': self.company.id,
            'date_start': date(2026, 4, 1),
            'date_end': date(2026, 4, 30),
        })
        run.action_compute_payroll()
        self.assertEqual(run.state, 'computed')

        run.action_review()
        self.assertEqual(run.state, 'reviewed')

        run.action_approve()
        self.assertEqual(run.state, 'approved')
        self.assertTrue(run.approved_by)

        run.action_confirm()
        self.assertEqual(run.state, 'confirmed')
