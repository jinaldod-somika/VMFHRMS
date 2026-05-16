from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from psycopg2.errors import UniqueViolation
from odoo.tools import mute_logger


class TestVmfMasterData(TransactionCase):
    """Cover the master-data extensions added for the FRD-driven templates:
    Company, Work Location, Department, Job Position, Employee.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Company = cls.env['res.company']
        cls.WorkLocation = cls.env['hr.work.location']
        cls.Department = cls.env['hr.department']
        cls.Job = cls.env['hr.job']
        cls.Employee = cls.env['hr.employee']
        cls.Region = cls.env['vmf.region']
        cls.Grade = cls.env['vmf.grade']

    def test_company_extension_fields(self):
        company = self.Company.create({
            'name': 'VMS DRC Test Co',
            'vmf_company_code': 'TEST-VMS',
            'vmf_short_name': 'VMS-T',
            'vmf_company_type': 'operating',
            'vmf_notes': 'Test entity for UAT.',
        })
        self.assertEqual(company.vmf_company_code, 'TEST-VMS')
        self.assertEqual(company.vmf_short_name, 'VMS-T')
        self.assertEqual(company.vmf_company_type, 'operating')
        self.assertIn('UAT', company.vmf_notes)

    def test_company_code_unique(self):
        self.Company.create({'name': 'X', 'vmf_company_code': 'DUPE-CODE'})
        self.env.flush_all()
        with self.assertRaises(Exception), \
             mute_logger('odoo.sql_db'):
            self.Company.create({'name': 'Y', 'vmf_company_code': 'DUPE-CODE'})
            self.env.flush_all()

    def test_work_location_extension_fields(self):
        region = self.Region.create({'name': 'Africa - Test', 'code': 'AFR-T'})
        partner = self.env['res.partner'].create({'name': 'Test Site Address'})
        loc = self.WorkLocation.create({
            'name': 'Test Site',
            'vmf_location_code': 'TST-SITE',
            'vmf_region_id': region.id,
            'vmf_notes': 'Test location notes.',
            'company_id': self.env.company.id,
            'location_type': 'office',
            'address_id': partner.id,
        })
        self.assertEqual(loc.vmf_location_code, 'TST-SITE')
        self.assertEqual(loc.vmf_region_id, region)
        self.assertIn('notes', loc.vmf_notes)

    def test_department_extension_fields(self):
        dept = self.Department.create({
            'name': 'Test HR Dept',
            'vmf_department_code': 'TST-HR',
            'vmf_notes': 'Reports to Group HR.',
        })
        self.assertEqual(dept.vmf_department_code, 'TST-HR')
        self.assertIn('Group HR', dept.vmf_notes)

    def test_job_position_grade_fields(self):
        grade = self.Grade.create({
            'name': 'TST-M5',
            'description': 'Test Manager Grade',
            'grade_level': 'management',
        })
        job = self.Job.create({
            'name': 'Test Manager Position',
            'grade_id': grade.id,
            'job_level': 'manager',
            'min_experience_years': 8,
            'is_critical_role': True,
        })
        self.assertEqual(job.grade_id, grade)
        self.assertEqual(job.grade_level, 'management')
        self.assertEqual(job.job_level, 'manager')
        self.assertEqual(job.min_experience_years, 8)
        self.assertTrue(job.is_critical_role)

    def test_employee_address_fields(self):
        emp = self.Employee.create({
            'name': 'Test Employee Address',
            'vmf_employee_category': 'expat_permanent',
            'vmf_permanent_address': '123 Main St, Mumbai, India',
            'vmf_current_address': '45 Mining Rd, Lubumbashi, DRC',
            'vmf_pan_number': 'ABCDE1234F',
            'vmf_aadhar_number': '1234-5678-9012',
            'vmf_uan_number': '100200300400',
            'vmf_pf_account': 'PF/MUM/12345',
            'vmf_esi_number': 'ESI/12345',
        })
        self.assertIn('Mumbai', emp.vmf_permanent_address)
        self.assertIn('Lubumbashi', emp.vmf_current_address)
        # India statutory fields are written; readback requires HR Manager
        # group which the test user has by default through admin.
        self.assertEqual(emp.vmf_pan_number, 'ABCDE1234F')
        self.assertEqual(emp.vmf_aadhar_number, '1234-5678-9012')
        self.assertEqual(emp.vmf_uan_number, '100200300400')
        self.assertEqual(emp.vmf_pf_account, 'PF/MUM/12345')
        self.assertEqual(emp.vmf_esi_number, 'ESI/12345')
