from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestVmfTravel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Travel Employee',
            'company_id': self.company.id,
            'vmf_employee_category': 'expat_permanent',
            'vmf_air_ticket_eligibility': 'once_year',
        })
        self.agent1 = self.env['vmf.travel.agent'].create({
            'name': 'Balaji Tour & Travels',
            'contact_person': 'Balaji',
            'applicable_routes': 'international',
        })
        self.agent2 = self.env['vmf.travel.agent'].create({
            'name': 'Satguru Travel',
            'contact_person': 'Satguru',
            'applicable_routes': 'all',
        })
        self.agent3 = self.env['vmf.travel.agent'].create({
            'name': 'Seven Seas Travel',
            'contact_person': 'Seven',
            'applicable_routes': 'international',
        })

    def _create_travel_request(self, **kwargs):
        vals = {
            'company_id': self.company.id,
            'employee_id': self.employee.id,
            'travel_purpose': 'annual_leave',
            'traveller_type': 'employee',
            'flight_type': 'international',
            'trip_type': 'two_way',
            'expected_departure_date': date.today() + timedelta(days=30),
            'expected_return_date': date.today() + timedelta(days=60),
        }
        vals.update(kwargs)
        return self.env['vmf.travel.request'].create(vals)

    def test_travel_request_sequence(self):
        req = self._create_travel_request()
        self.assertNotEqual(req.name, 'New')
        self.assertIn('TRV-', req.name)

    def test_travel_approval_workflow(self):
        req = self._create_travel_request()
        self.assertEqual(req.state, 'draft')

        req.action_submit()
        self.assertEqual(req.state, 'submitted')

        req.action_manager_approve()
        self.assertEqual(req.state, 'manager_approved')

        req.action_hr_approve()
        self.assertEqual(req.state, 'hr_approved')

        req.action_send_to_travel_desk()
        self.assertEqual(req.state, 'travel_desk')

    def test_quotation_lowest_detection(self):
        req = self._create_travel_request()
        req.action_submit()
        req.action_manager_approve()
        req.action_hr_approve()
        req.action_send_to_travel_desk()

        # Add quotations
        q1 = self.env['vmf.travel.quotation'].create({
            'request_id': req.id,
            'agent_id': self.agent1.id,
            'quoted_amount': 1500,
            'ticket_class': 'economy',
        })
        q2 = self.env['vmf.travel.quotation'].create({
            'request_id': req.id,
            'agent_id': self.agent2.id,
            'quoted_amount': 1200,  # Lowest
            'ticket_class': 'economy',
        })
        q3 = self.env['vmf.travel.quotation'].create({
            'request_id': req.id,
            'agent_id': self.agent3.id,
            'quoted_amount': 1800,
            'ticket_class': 'economy',
        })

        # Check lowest flag
        self.assertFalse(q1.is_lowest)
        self.assertTrue(q2.is_lowest)
        self.assertFalse(q3.is_lowest)

    def test_cost_computation(self):
        req = self._create_travel_request()
        req.write({
            'international_cost': 1200,
            'domestic_cost': 150,
            'seat_charges': 25,
        })
        self.assertEqual(req.overall_cost, 1375)

    def test_company_cost_share(self):
        req = self._create_travel_request()
        req.write({
            'international_cost': 1200,
            'domestic_cost': 150,
            'seat_charges': 25,
            'employee_cost_share': 200,
        })
        self.assertEqual(req.company_cost_share, 1175)

    def test_route_computation(self):
        airport_bom = self.env['vmf.airport'].search([('code', '=', 'BOM')], limit=1)
        airport_dxb = self.env['vmf.airport'].search([('code', '=', 'DXB')], limit=1)
        airport_lub = self.env['vmf.airport'].search([('code', '=', 'LUB')], limit=1)

        if airport_bom and airport_dxb and airport_lub:
            req = self._create_travel_request(
                origin_airport_id=airport_bom.id,
                via_airport_id=airport_dxb.id,
                destination_airport_id=airport_lub.id,
            )
            self.assertEqual(req.route_description, 'BOM → DXB → LUB')

    def test_travel_booking_and_travelled(self):
        req = self._create_travel_request()
        req.action_submit()
        req.action_manager_approve()
        req.action_hr_approve()
        req.action_send_to_travel_desk()
        req.write({'ticket_number': 'ET-001-TEST', 'pnr_number': 'PNR123'})
        req.action_book()
        self.assertEqual(req.state, 'booked')
        req.action_mark_travelled()
        self.assertEqual(req.state, 'travelled')
