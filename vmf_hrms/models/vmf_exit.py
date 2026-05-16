from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import date


class VmfExitRequest(models.Model):
    _name = 'vmf.exit.request'
    _description = 'Exit Request / Separation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char('Exit Reference', readonly=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)

    exit_type = fields.Selection([
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('contract_end', 'Contract End'),
        ('retirement', 'Retirement'),
        ('mutual_separation', 'Mutual Separation'),
        ('absconding', 'Absconding'),
        ('death', 'Death'),
    ], string='Exit Type', required=True, tracking=True)

    resignation_date = fields.Date('Resignation Date', default=fields.Date.today)
    last_working_date = fields.Date('Last Working Date', required=True, tracking=True)
    notice_period_days = fields.Integer('Notice Period (days)')
    notice_served_days = fields.Integer('Notice Days Served', compute='_compute_notice_days', store=True)
    notice_shortfall_days = fields.Integer('Notice Shortfall', compute='_compute_notice_days', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('manager_approved', 'Manager Approved'),
        ('hr_processing', 'HR Processing'),
        ('clearance_in_progress', 'Clearance in Progress'),
        ('ff_computed', 'F&F Computed'),
        ('ff_approved', 'F&F Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # No-dues clearance
    clearance_ids = fields.One2many('vmf.exit.clearance', 'exit_id', string='Clearance Items')
    clearance_complete = fields.Boolean('All Clearances Done', compute='_compute_clearance_complete', store=True)

    # Exit interview
    exit_interview_done = fields.Boolean('Exit Interview Done')
    exit_interview_date = fields.Date('Exit Interview Date')
    exit_reason_detail = fields.Text('Detailed Exit Reason')
    would_rejoin = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe'),
    ], string='Would Rejoin?')

    # F&F Settlement
    ff_settlement_id = fields.Many2one('vmf.ff.settlement', string='F&F Settlement', readonly=True)

    # Documents generated
    relieving_letter_generated = fields.Boolean('Relieving Letter Generated')
    experience_letter_generated = fields.Boolean('Experience Certificate Generated')

    notes = fields.Text('Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.exit.request') or 'New'
        return super().create(vals_list)

    @api.depends('resignation_date', 'last_working_date', 'notice_period_days')
    def _compute_notice_days(self):
        for rec in self:
            if rec.resignation_date and rec.last_working_date:
                served = (rec.last_working_date - rec.resignation_date).days
                rec.notice_served_days = served
                rec.notice_shortfall_days = max(0, (rec.notice_period_days or 0) - served)
            else:
                rec.notice_served_days = 0
                rec.notice_shortfall_days = 0

    @api.depends('clearance_ids.status')
    def _compute_clearance_complete(self):
        for rec in self:
            if not rec.clearance_ids:
                rec.clearance_complete = False
            else:
                rec.clearance_complete = all(c.status == 'cleared' for c in rec.clearance_ids)

    def action_submit(self):
        self.write({'state': 'submitted'})
        # Auto-create clearance items
        self._create_clearance_items()
        self.message_post(body=_('Exit request submitted. Clearance items created.'))

    def _create_clearance_items(self):
        departments = ['IT', 'Admin', 'Finance', 'HR', 'Security', 'Transport']
        for dept in departments:
            existing = self.clearance_ids.filtered(lambda c: c.department_name == dept)
            if not existing:
                self.env['vmf.exit.clearance'].create({
                    'exit_id': self.id,
                    'department_name': dept,
                    'status': 'pending',
                })

    def action_manager_approve(self):
        self.write({'state': 'manager_approved'})

    def action_hr_process(self):
        self.write({'state': 'hr_processing'})

    def action_compute_ff(self):
        self.ensure_one()
        if not self.ff_settlement_id:
            ff = self.env['vmf.ff.settlement'].create({
                'exit_id': self.id,
                'employee_id': self.employee_id.id,
                'last_working_date': self.last_working_date,
            })
            ff.action_compute()
            self.ff_settlement_id = ff
        self.write({'state': 'ff_computed'})

    def action_approve_ff(self):
        self.write({'state': 'ff_approved'})

    def action_complete(self):
        self.ensure_one()
        # Mark all clearances as cleared
        self.clearance_ids.write({
            'status': 'cleared',
            'cleared_date': fields.Date.today()
        })
        self.write({'state': 'completed'})
        # Archive employee
        self.employee_id.write({
            'active': False,
            'vmf_exit_reason': self.exit_type,
        })
        self.message_post(body=_('Exit process completed. Employee archived.'))


class VmfExitClearance(models.Model):
    _name = 'vmf.exit.clearance'
    _description = 'Exit Clearance Item'
    _order = 'department_name'

    exit_id = fields.Many2one('vmf.exit.request', string='Exit Request', required=True, ondelete='cascade')
    department_name = fields.Char('Department / Function', required=True)
    responsible_id = fields.Many2one('hr.employee', string='Responsible Person')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('cleared', 'Cleared'),
        ('hold', 'On Hold'),
    ], string='Status', default='pending')
    remarks = fields.Text('Remarks')
    cleared_date = fields.Date('Cleared Date')
    assets_to_recover = fields.Text('Assets to Recover')
    amount_to_recover = fields.Monetary('Amount to Recover', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    def action_clear(self):
        self.write({'status': 'cleared', 'cleared_date': fields.Date.today()})


class VmfFFSettlement(models.Model):
    _name = 'vmf.ff.settlement'
    _description = 'Full & Final Settlement'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char('F&F Reference', readonly=True, copy=False, default='New')
    exit_id = fields.Many2one('vmf.exit.request', string='Exit Request', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    last_working_date = fields.Date('Last Working Date')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Earnings
    unpaid_salary = fields.Monetary('Unpaid Salary', currency_field='currency_id')
    leave_encashment_days = fields.Float('Leave Encashment Days')
    leave_encashment_amount = fields.Monetary('Leave Encashment Amount', currency_field='currency_id')
    bonus_arrears = fields.Monetary('Bonus / Arrears', currency_field='currency_id')
    gratuity_amount = fields.Monetary('Gratuity Amount', currency_field='currency_id')

    # Deductions
    notice_recovery = fields.Monetary('Notice Period Recovery', currency_field='currency_id')
    advance_recovery = fields.Monetary('Advance Recovery', currency_field='currency_id')
    loan_recovery = fields.Monetary('Loan Recovery', currency_field='currency_id')
    asset_recovery = fields.Monetary('Asset Recovery', currency_field='currency_id')
    other_deductions = fields.Monetary('Other Deductions', currency_field='currency_id')

    total_earnings = fields.Monetary('Total Earnings', compute='_compute_totals', store=True,
                                     currency_field='currency_id')
    total_deductions = fields.Monetary('Total Deductions', compute='_compute_totals', store=True,
                                       currency_field='currency_id')
    net_settlement = fields.Monetary('Net Settlement', compute='_compute_totals', store=True,
                                     currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ], string='Status', default='draft')
    notes = fields.Text('Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.ff.settlement') or 'New'
        return super().create(vals_list)

    @api.depends('unpaid_salary', 'leave_encashment_amount', 'bonus_arrears', 'gratuity_amount',
                 'notice_recovery', 'advance_recovery', 'loan_recovery', 'asset_recovery', 'other_deductions')
    def _compute_totals(self):
        for rec in self:
            rec.total_earnings = (rec.unpaid_salary + rec.leave_encashment_amount +
                                  rec.bonus_arrears + rec.gratuity_amount)
            rec.total_deductions = (rec.notice_recovery + rec.advance_recovery +
                                    rec.loan_recovery + rec.asset_recovery + rec.other_deductions)
            rec.net_settlement = rec.total_earnings - rec.total_deductions

    def action_compute(self):
        """Auto-compute F&F based on employee data"""
        self.ensure_one()
        # Leave encashment days (to be filled by HR)
        self.state = 'computed'

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})
