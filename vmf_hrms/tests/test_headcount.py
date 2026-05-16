from odoo.tests.common import TransactionCase
from datetime import date


class TestVmfHeadcount(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company

    def _create_employee(self, category):
        return self.env['hr.employee'].create({
            'name': f'Test {category} Employee',
            'company_id': self.company.id,
            'vmf_employee_category': category,
        })

    def test_headcount_snapshot_generation(self):
        # Create some employees in different categories
        self._create_employee('expat_permanent')
        self._create_employee('expat_permanent')
        self._create_employee('expat_contractual')
        self._create_employee('national_permanent')
        self._create_employee('national_contractual')
        self._create_employee('security_agency')

        snapshots = self.env['vmf.headcount.snapshot'].generate_snapshot(
            snapshot_date=date(2026, 3, 1),
            company_ids=[self.company.id],
        )
        self.assertEqual(len(snapshots), 1)
        snap = snapshots[0]

        self.assertEqual(snap.expat_permanent, 2)
        self.assertEqual(snap.expat_contractual, 1)
        self.assertEqual(snap.national_permanent, 1)
        self.assertEqual(snap.national_contractual, 1)
        self.assertEqual(snap.security_agency, 1)
        self.assertEqual(snap.total_headcount, 6)
        self.assertEqual(snap.expat_total, 3)
        self.assertEqual(snap.national_total, 3)

    def test_headcount_variance_calculation(self):
        snap = self.env['vmf.headcount.snapshot'].create({
            'snapshot_date': date(2026, 3, 1),
            'company_id': self.company.id,
            'expat_permanent': 10,
            'national_permanent': 20,
            'prior_month_total': 28,
        })
        self.assertEqual(snap.total_headcount, 30)
        self.assertEqual(snap.variance, 2)
        # Variance % = 2/28 * 100 ≈ 7.14
        self.assertAlmostEqual(snap.variance_pct, 7.142857, places=2)

    def test_headcount_ratio(self):
        snap = self.env['vmf.headcount.snapshot'].create({
            'snapshot_date': date(2026, 3, 1),
            'company_id': self.company.id,
            'expat_permanent': 10,
            'national_permanent': 20,
        })
        # Expat:National = 10:20 = 0.50:1
        self.assertEqual(snap.expat_national_ratio, '0.50:1')

    def test_snapshot_name_format(self):
        snap = self.env['vmf.headcount.snapshot'].create({
            'snapshot_date': date(2026, 3, 1),
            'company_id': self.company.id,
        })
        self.assertIn('HC/', snap.name)
        self.assertIn('Mar 2026', snap.name)
