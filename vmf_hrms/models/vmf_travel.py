from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from datetime import date


class VmfTravelAgent(models.Model):
    _name = 'vmf.travel.agent'
    _description = 'Travel Agent Master'
    _order = 'name'
    _rec_names_search = ['name']

    name = fields.Char('Agent Name', required=True)
    contact_person = fields.Char('Contact Person')
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    applicable_routes = fields.Selection([
        ('international', 'International'),
        ('domestic_india', 'Domestic India'),
        ('domestic_drc', 'Domestic DRC'),
        ('all', 'All Routes'),
    ], string='Applicable Routes', default='all')
    active = fields.Boolean('Active', default=True)


class VmfTravelRequest(models.Model):
    _name = 'vmf.travel.request'
    _description = 'Travel Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'
    _rec_names_search = ['name'] # Travel Request No.

    name = fields.Char('Travel Request No.', readonly=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)

    travel_purpose = fields.Selection([
        ('new_joinee', 'New Joinee'),
        ('leave_returnee', 'Leave Returnee'),
        ('annual_leave', 'Annual Leave Travel'),
        ('emergency', 'Emergency'),
        ('business', 'Business Travel'),
        ('family_travel', 'Family Travel'),
        ('transfer', 'Transfer'),
        ('demobilisation', 'Demobilisation'),
        ('medical', 'Medical Travel'),
        ('training', 'Training'),
        ('other', 'Other'),
    ], string='Travel Purpose', required=True, tracking=True)

    traveller_type = fields.Selection([
        ('employee', 'Employee'),
        ('family', 'Family Member'),
        ('consultant', 'Consultant'),
        ('visitor', 'Visitor'),
    ], string='Traveller Type', default='employee', required=True)

    traveller_name = fields.Char('Traveller Name', compute='_compute_traveller_name', store=True)
    family_member_name = fields.Char('Family Member Name', help='If traveller type is Family')
    relation = fields.Char('Relation to Employee')

    flight_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International'),
        ('both', 'Domestic + International'),
    ], string='Flight Type', required=True, default='international')

    trip_type = fields.Selection([
        ('one_way', 'One Way'),
        ('two_way', 'Two Way / Return'),
    ], string='Trip Type', required=True, default='two_way')

    origin_airport_id = fields.Many2one('vmf.airport', string='Origin Airport')
    destination_airport_id = fields.Many2one('vmf.airport', string='Destination Airport')
    via_airport_id = fields.Many2one('vmf.airport', string='Via Airport (connecting)')
    route_description = fields.Char('Route', compute='_compute_route', store=True)

    expected_departure_date = fields.Date('Expected Departure Date', required=True, tracking=True)
    expected_return_date = fields.Date('Expected Return Date')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('manager_approved', 'Manager Approved'),
        ('hr_approved', 'HR Approved'),
        ('travel_desk', 'With Travel Desk'),
        ('booked', 'Booked'),
        ('travelled', 'Travelled'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ], string='Status', default='draft', tracking=True)

    # Passport & visa
    passport_number = fields.Char('Passport No.', related='employee_id.vmf_passport_number', store=True)
    passport_expiry = fields.Date('Passport Expiry', related='employee_id.vmf_passport_expiry', store=True)
    visa_type = fields.Selection([
        ('pec', 'PEC'),
        ('vvl', 'VVL'),
        ('not_required', 'Not Required'),
        ('business', 'Business Visa'),
        ('other', 'Other'),
    ], string='Visa Type')
    visa_status = fields.Selection([
        ('not_required', 'Not Required'),
        ('to_apply', 'To Apply'),
        ('applied', 'Applied'),
        ('received', 'Received'),
        ('rejected', 'Rejected'),
    ], string='Visa Status', default='not_required')
    visa_application_date = fields.Date('Visa Application Date')
    visa_received_date = fields.Date('Visa Received Date')

    # Quotations
    quotation_ids = fields.One2many('vmf.travel.quotation', 'request_id', string='Agent Quotations')
    selected_quotation_id = fields.Many2one('vmf.travel.quotation', string='Selected Quotation',
                                            domain="[('request_id', '=', id)]")
    booking_agent_id = fields.Many2one('vmf.travel.agent', related='selected_quotation_id.agent_id',
                                       store=True, string='Booking Agent')
    selection_justification = fields.Text('Selection Justification',
                                          help='Required if not selecting the lowest price quote')

    # Ticket details
    ticket_number = fields.Char('Ticket Number / Reference')
    pnr_number = fields.Char('PNR')
    airline = fields.Char('Airline(s)')
    ticket_class = fields.Selection([
        ('economy', 'Economy'),
        ('premium_economy', 'Premium Economy'),
        ('business', 'Business Class'),
        ('first', 'First Class'),
    ], string='Ticket Class', default='economy')
    ticket_issue_date = fields.Date('Ticket Issue Date')
    dummy_ticket = fields.Boolean('Dummy Ticket')
    dummy_ticket_pnr = fields.Char('Dummy PNR')

    # Actual travel dates
    actual_departure_date = fields.Date('Actual Departure Date')
    actual_return_date = fields.Date('Actual Return Date')

    # Cost computation
    international_cost = fields.Monetary('International Ticket Cost', currency_field='currency_id')
    domestic_cost = fields.Monetary('Domestic Ticket Cost', currency_field='currency_id')
    seat_charges = fields.Monetary('Seat Charges / MCO', currency_field='currency_id')
    overall_cost = fields.Monetary('Overall Trip Cost', compute='_compute_overall_cost', store=True,
                                   currency_field='currency_id')
    employee_cost_share = fields.Monetary('Employee Cost Share', currency_field='currency_id')
    company_cost_share = fields.Monetary('Company Cost Share', compute='_compute_company_share', store=True,
                                         currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    notes = fields.Text('Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.travel.request') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        restricted_fields = {
            'ticket_number', 'pnr_number', 'airline', 'ticket_class', 'ticket_issue_date',
            'dummy_ticket', 'dummy_ticket_pnr', 'international_cost', 'domestic_cost',
            'seat_charges', 'employee_cost_share', 'currency_id'
        }
        for rec in self:
            if rec.state in ['travelled', 'cancelled']:
                if any(key != 'state' for key in vals.keys()):
                    raise ValidationError(_("You cannot modify a travel request that is already in '%s' state.") % rec.state)
            if restricted_fields.intersection(vals.keys()):
                if not (self.env.user.has_group('vmf_hrms.group_vmf_travel_desk') or 
                        self.env.user.has_group('vmf_hrms.group_vmf_hr_manager') or 
                        self.env.is_admin() or 
                        self.env.su):
                    raise ValidationError(_("Only Travel Desk Co-ordinators or HR Managers can modify ticket and cost details."))
        return super().write(vals)

    @api.depends('traveller_type', 'employee_id', 'family_member_name')
    def _compute_traveller_name(self):
        for rec in self:
            if rec.traveller_type == 'employee':
                rec.traveller_name = rec.employee_id.name if rec.employee_id else ''
            else:
                rec.traveller_name = rec.family_member_name or ''

    @api.depends('origin_airport_id', 'destination_airport_id', 'via_airport_id')
    def _compute_route(self):
        for rec in self:
            parts = []
            if rec.origin_airport_id:
                parts.append(rec.origin_airport_id.code)
            if rec.via_airport_id:
                parts.append(rec.via_airport_id.code)
            if rec.destination_airport_id:
                parts.append(rec.destination_airport_id.code)
            rec.route_description = ' → '.join(parts)

    @api.depends('international_cost', 'domestic_cost', 'seat_charges')
    def _compute_overall_cost(self):
        for rec in self:
            rec.overall_cost = rec.international_cost + rec.domestic_cost + rec.seat_charges

    @api.depends('overall_cost', 'employee_cost_share')
    def _compute_company_share(self):
        for rec in self:
            rec.company_cost_share = max(0, rec.overall_cost - rec.employee_cost_share)

    def action_submit(self):
        self.write({'state': 'submitted'})
        self.message_post(body=_('Travel request submitted for approval.'))

    def action_manager_approve(self):
        self.write({'state': 'manager_approved'})

    def action_hr_approve(self):
        self.write({'state': 'hr_approved'})

    def action_send_to_travel_desk(self):
        self.write({'state': 'travel_desk'})
        self.message_post(body=_('Travel request sent to Travel Desk for booking.'))

    def action_book(self):
        for rec in self:
            if not rec.selected_quotation_id:
                raise ValidationError(_("Selected Quotation is required before booking."))
            if not rec.ticket_number:
                raise ValidationError(_("Ticket Number / Reference is required before booking."))
            if not rec.pnr_number:
                raise ValidationError(_("PNR is required before booking."))
            if not rec.airline:
                raise ValidationError(_("Airline(s) is required before booking."))
            if not rec.ticket_issue_date:
                raise ValidationError(_("Ticket Issue Date is required before booking."))
            if not rec.overall_cost or rec.overall_cost <= 0:
                raise ValidationError(_("Overall Trip Cost must be greater than 0 before booking. Please ensure cost details are populated."))
        self.write({'state': 'booked'})
        self.message_post(body=_('Ticket booked. Details: %s') % (self.ticket_number or 'N/A'))

    def action_mark_travelled(self):
        self.write({'state': 'travelled', 'actual_departure_date': date.today()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class VmfTravelQuotation(models.Model):
    _name = 'vmf.travel.quotation'
    _description = 'Travel Agent Quotation'
    _order = 'quoted_amount'
    _rec_name = 'name'

    name = fields.Char('Quotation No.', readonly=True, copy=False, default='New')
    request_id = fields.Many2one('vmf.travel.request', string='Travel Request', required=True, ondelete='cascade')
    agent_id = fields.Many2one('vmf.travel.agent', string='Travel Agent', required=True)
    quoted_amount = fields.Monetary('Quoted Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', related='request_id.currency_id', store=True)
    airlines = fields.Char('Airlines / Route Details')
    ticket_class = fields.Selection([
        ('economy', 'Economy'),
        ('premium_economy', 'Premium Economy'),
        ('business', 'Business Class'),
    ], string='Class', default='economy')
    validity_date = fields.Date('Quote Validity')
    notes = fields.Text('Notes')
    is_lowest = fields.Boolean('Lowest Price', compute='_compute_is_lowest', store=True)
    is_selected = fields.Boolean('Selected', compute='_compute_is_selected', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('vmf.travel.quotation') or 'New'
                agent_name = ""
                if vals.get('agent_id'):
                    agent = self.env['vmf.travel.agent'].browse(vals['agent_id'])
                    if agent:
                        agent_name = f" - {agent.name}"
                vals['name'] = f"{seq}{agent_name}"
        return super().create(vals_list)

    @api.depends('request_id.quotation_ids.quoted_amount')
    def _compute_is_lowest(self):
        for rec in self:
            if rec.request_id.quotation_ids:
                min_amt = min(rec.request_id.quotation_ids.mapped('quoted_amount'))
                rec.is_lowest = rec.quoted_amount == min_amt
            else:
                rec.is_lowest = False

    @api.depends('request_id.selected_quotation_id')
    def _compute_is_selected(self):
        for rec in self:
            rec.is_selected = rec.request_id.selected_quotation_id == rec
