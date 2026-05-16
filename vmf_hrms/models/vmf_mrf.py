from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
from datetime import date


class VmfMRF(models.Model):
    _name = 'vmf.mrf'
    _description = 'Manpower Requisition Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char('Position UID', readonly=True, copy=False, default='Draft')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, tracking=True)
    job_id = fields.Many2one('hr.job', string='Designation / Job Position', required=True, tracking=True)
    grade_id = fields.Many2one('vmf.grade', string='Grade', tracking=True)
    business_unit_id = fields.Many2one('vmf.business.unit', string='Business Unit')
    work_location_id = fields.Many2one('hr.work.location', string='Work Location')

    requisition_type = fields.Selection([
        ('new_hire', 'New Hire'),
        ('replacement', 'Replacement'),
        ('contract_renewal', 'Contract Renewal'),
        ('transfer', 'Transfer'),
    ], string='Requisition Type', required=True, default='new_hire', tracking=True)

    employment_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('subcontract', 'Subcontract'),
        ('agency', 'Security / Agency'),
    ], string='Employment Type', required=True, default='permanent', tracking=True)

    employment_duration = fields.Integer('Duration (months)', help='For contract positions')

    employee_category = fields.Selection([
        ('expat_permanent', 'Expat Permanent'),
        ('expat_contractual', 'Expat Contractual'),
        ('national_permanent', 'National Permanent'),
        ('national_contractual', 'National Contractual'),
        ('security_agency', 'Security / Agency'),
        ('subcontractor', 'Subcontractor'),
    ], string='Employee Category', required=True, tracking=True)

    priority = fields.Selection([
        ('critical', 'Critical'),
        ('normal', 'Normal'),
        ('low', 'Low'),
    ], string='Business Priority', default='normal', tracking=True)

    no_of_positions = fields.Integer('Number of Positions', default=1, required=True)
    filled_positions = fields.Integer('Filled Positions', compute='_compute_filled_positions', store=True)
    open_positions = fields.Integer('Open Positions', compute='_compute_filled_positions', store=True)

    replacement_employee_id = fields.Many2one('hr.employee', string='Replacement For',
                                               help='For replacement requisitions')

    hiring_manager_id = fields.Many2one('hr.employee', string='Hiring Manager', required=True)
    coordinator_id = fields.Many2one('hr.employee', string='Recruiter / Coordinator')

    budget_currency_id = fields.Many2one('res.currency', string='Budget Currency',
                                          default=lambda self: self.env.company.currency_id)
    budget_min = fields.Monetary('Budget Min', currency_field='budget_currency_id')
    budget_max = fields.Monetary('Budget Max', currency_field='budget_currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('dept_approved', 'Dept. Manager Approved'),
        ('hr_approved', 'BU HR Approved'),
        ('group_hr_approved', 'Group HR Approved'),
        ('budget_approved', 'Budget Approved / Open'),
        ('in_progress', 'In Progress'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ], string='Status', default='draft', tracking=True)

    previous_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('dept_approved', 'Dept. Manager Approved'),
        ('hr_approved', 'BU HR Approved'),
        ('group_hr_approved', 'Group HR Approved'),
        ('budget_approved', 'Budget Approved / Open'),
        ('in_progress', 'In Progress'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ], string='Previous Status', help='Stores the state before putting on hold')

    hold_reason = fields.Text('Current Hold Reason')

    date_submitted = fields.Date('Date Submitted', readonly=True)
    date_dept_approved = fields.Date('Dept. Approved Date', readonly=True)
    date_hr_approved = fields.Date('HR Approved Date', readonly=True)
    date_group_hr_approved = fields.Date('Group HR Approved Date', readonly=True)
    date_budget_approved = fields.Date('Budget Approved Date', readonly=True)
    date_target_fill = fields.Date('Target Fill Date')

    # Position age tracking
    position_age_days = fields.Integer('Position Age (days)', compute='_compute_position_age', store=False)
    hold_days = fields.Integer('Hold Days', compute='_compute_hold_days', store=False)
    effective_age_days = fields.Integer('Effective Age (days)', compute='_compute_position_age', store=False)

    justification = fields.Text('Business Justification', required=True)
    job_description = fields.Html('Job Description')
    skills_required = fields.Text('Skills Required')
    qualifications = fields.Text('Qualifications Required')

    # Hold tracking
    hold_line_ids = fields.One2many('vmf.mrf.hold', 'mrf_id', string='Hold Log')

    # Linked candidates
    candidate_ids = fields.One2many('vmf.candidate', 'mrf_id', string='Candidates')
    candidate_count = fields.Integer('Candidate Count', compute='_compute_candidate_count', store=True)

    notes = fields.Text('Internal Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Draft') == 'Draft':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.mrf') or 'Draft'
        return super().create(vals_list)

    @api.depends('candidate_ids', 'candidate_ids.state')
    def _compute_filled_positions(self):
        for rec in self:
            joined = rec.candidate_ids.filtered(lambda c: c.state == 'joined')
            rec.filled_positions = len(joined)
            rec.open_positions = max(0, rec.no_of_positions - rec.filled_positions)

    @api.depends('candidate_ids')
    def _compute_candidate_count(self):
        for rec in self:
            rec.candidate_count = len(rec.candidate_ids)

    def _compute_position_age(self):
        today = date.today()
        for rec in self:
            start = rec.date_budget_approved or rec.date_submitted or (rec.create_date and rec.create_date.date())
            rec.position_age_days = (today - start).days if start else 0
            hold = sum(h.hold_days for h in rec.hold_line_ids if h.hold_days)
            rec.hold_days = hold
            rec.effective_age_days = max(0, rec.position_age_days - hold)

    def _compute_hold_days(self):
        for rec in self:
            rec.hold_days = sum(h.hold_days for h in rec.hold_line_ids if h.hold_days)

    def action_submit(self):
        self.ensure_one()
        self.write({'state': 'submitted', 'date_submitted': date.today()})
        self.message_post(body=_('MRF submitted for approval.'))

    def action_dept_approve(self):
        self.ensure_one()
        self.write({'state': 'dept_approved', 'date_dept_approved': date.today()})
        self.message_post(body=_('Approved by Department Manager.'))

    def action_hr_approve(self):
        self.ensure_one()
        self.write({'state': 'hr_approved', 'date_hr_approved': date.today()})
        self.message_post(body=_('Approved by BU HR.'))

    def action_group_hr_approve(self):
        self.ensure_one()
        self.write({'state': 'group_hr_approved', 'date_group_hr_approved': date.today()})
        self.message_post(body=_('Approved by Group HR.'))

    def action_budget_approve(self):
        self.ensure_one()
        if not self.budget_max:
            raise exceptions.UserError(_('Please define budget before budget approval.'))
        self.write({'state': 'budget_approved', 'date_budget_approved': date.today()})
        self.message_post(body=_('Budget approved. Position is now OPEN for recruitment.'))

    def action_set_in_progress(self):
        self.ensure_one()
        self.write({'state': 'in_progress'})

    def action_hold(self):
        self.ensure_one()
        self.write({'state': 'on_hold'})
        self.message_post(body=_('Position placed on hold.'))

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
        self.message_post(body=_('MRF cancelled.'))

    def action_reopen(self):
        self.ensure_one()
        state_to_restore = self.previous_state or 'budget_approved'
        self.write({'state': state_to_restore})
        self.message_post(body=_('Position reopened to state: %s') % state_to_restore)

    def action_filled(self):
        self.ensure_one()
        self.write({'state': 'filled'})
        self.message_post(body=_('MRF marked as filled/closed.'))

    def action_view_candidates(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Candidates',
            'res_model': 'vmf.candidate',
            'view_mode': 'list,form',
            'domain': [('mrf_id', '=', self.id)],
            'context': {'default_mrf_id': self.id},
        }


class VmfMRFHold(models.Model):
    _name = 'vmf.mrf.hold'
    _description = 'MRF Hold Log'
    _order = 'hold_start_date desc'

    mrf_id = fields.Many2one('vmf.mrf', string='MRF', required=True, ondelete='cascade')
    hold_start_date = fields.Date('Hold Start Date', required=True, default=fields.Date.today)
    hold_end_date = fields.Date('Hold End Date')
    hold_reason = fields.Text('Hold Reason', required=True)
    reopen_reason = fields.Text('Reopen Reason')
    previous_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('dept_approved', 'Dept. Manager Approved'),
        ('hr_approved', 'BU HR Approved'),
        ('group_hr_approved', 'Group HR Approved'),
        ('budget_approved', 'Budget Approved / Open'),
        ('in_progress', 'In Progress'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ], string='Previous Status')
    hold_days = fields.Integer('Hold Days', compute='_compute_hold_days', store=True)
    resumed_by = fields.Many2one('res.users', string='Resumed By')

    @api.depends('hold_start_date', 'hold_end_date')
    def _compute_hold_days(self):
        for rec in self:
            if rec.hold_start_date and rec.hold_end_date:
                rec.hold_days = (rec.hold_end_date - rec.hold_start_date).days
            else:
                rec.hold_days = 0
