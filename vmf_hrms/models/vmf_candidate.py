from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import date


SOURCING_CHANNELS = [
    ('karmaa', 'Karmaa'),
    ('referral', 'Referral'),
    ('linkedin', 'LinkedIn'),
    ('elite_solutions', 'Elite Solutions'),
    ('uv_hr', 'UV HR'),
    ('talastra', 'Talastra'),
    ('naukri', 'Naukri.com'),
    ('indeed', 'Indeed'),
    ('internal', 'Internal Transfer'),
    ('walk_in', 'Walk-in'),
    ('other', 'Other'),
]

INTERVIEW_RESULTS = [
    ('scheduled', 'Scheduled'),
    ('cleared', 'Cleared'),
    ('rejected', 'Rejected'),
    ('result_pending', 'Result Pending'),
    ('no_show', 'No Show'),
]

ASSESSMENT_RESULTS = [
    ('recommended', 'Recommended'),
    ('cautiously_recommended', 'Cautiously Recommended'),
    ('not_recommended', 'Not Recommended'),
    ('exception', 'Exception'),
    ('pending', 'Pending'),
]


class VmfCandidate(models.Model):
    _name = 'vmf.candidate'
    _description = 'Candidate Lifecycle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'
    _rec_names_search = ['name', 'candidate_name']

    name = fields.Char('Candidate UID', readonly=True, copy=False, default='New')
    candidate_name = fields.Char('Candidate Name', required=True, tracking=True)
    mobile = fields.Char('Mobile')
    email = fields.Char('Email')
    mrf_id = fields.Many2one('vmf.mrf', string='Position (MRF)', required=True, tracking=True,
                             domain="[('state', 'in', ['budget_approved', 'in_progress'])]")
    company_id = fields.Many2one('res.company', related='mrf_id.company_id', store=True, string='Company')
    department_id = fields.Many2one('hr.department', related='mrf_id.department_id', store=True)
    job_id = fields.Many2one('hr.job', related='mrf_id.job_id', store=True, string='Applied For')
    grade_id = fields.Many2one('vmf.grade', related='mrf_id.grade_id', store=True)

    sourcing_channel = fields.Selection(SOURCING_CHANNELS, string='Sourcing Channel', tracking=True)
    sourcing_agency = fields.Char('Agency / Partner Name')
    resume_received_date = fields.Date('Resume Received Date', default=fields.Date.today)
    coordinator_id = fields.Many2one('hr.employee', string='Coordinator / Recruiter', tracking=True)
    hiring_manager_id = fields.Many2one('hr.employee', string='Hiring Manager', tracking=True)

    state = fields.Selection([
        ('new', 'New'),
        ('screening', 'Screening'),
        ('invitation_1', '1st Round Invitation Sent'),
        ('interview_1', 'Interview Round 1'),
        ('invitation_2', '2nd Round Invitation Sent'),
        ('interview_2', 'Interview Round 2'),
        ('invitation_3', '3rd Round Invitation Sent'),
        ('interview_3', 'Interview Round 3'),
        ('assessment', 'Assessment'),
        ('selected', 'Selected'),
        ('offer_prepared', 'Offer Prepared'),
        ('offer_released', 'Offer Released'),
        ('offer_accepted', 'Offer Accepted'),
        ('bgv', 'BGV in Progress'),
        ('medical', 'Medical Clearance'),
        ('visa', 'Visa / PEC Processing'),
        ('joining_confirmed', 'Joining Confirmed'),
        ('joined', 'Joined'),
        ('offer_dropped', 'Offer Dropped'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ], string='Status', default='new', tracking=True)

    previous_state = fields.Selection([
        ('new', 'New'),
        ('screening', 'Screening'),
        ('invitation_1', '1st Round Invitation Sent'),
        ('interview_1', 'Interview 1'),
        ('invitation_2', '2nd Round Invitation Sent'),
        ('interview_2', 'Interview 2'),
        ('invitation_3', '3rd Round Invitation Sent'),
        ('interview_3', 'Interview 3'),
        ('selected', 'Selected'),
        ('offer_prepared', 'Offer Prepared'),
        ('offer_released', 'Offer Released'),
        ('offer_accepted', 'Offer Accepted'),
        ('bgv', 'BGV / Medical / Visa'),
        ('joining_confirmed', 'Joining Confirmed'),
        ('joined', 'Joined'),
        ('offer_dropped', 'Offer Dropped'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ], string='Previous Status')

    hold_reason = fields.Text('Current Hold Reason')
    drop_reason = fields.Text('Current Drop Reason')

    # Interview rounds
    interview1_date = fields.Date('Round 1 Date')
    interview1_interviewer_ids = fields.Many2many('hr.employee', 'cand_int1_rel', 'cand_id', 'emp_id', string='Round 1 Interviewers')
    interview1_hr_interviewer_id = fields.Many2one('hr.employee', string='Round 1 HR Interviewer')
    interview1_google_meet_link = fields.Char('Round 1 Google Meet Link')
    interview1_result = fields.Selection(INTERVIEW_RESULTS, string='Round 1 Result')
    interview1_feedback = fields.Text('Round 1 Feedback')
    interview1_remarks = fields.Text('Round 1 Remarks')

    interview2_date = fields.Date('Round 2 Date')
    interview2_interviewer_ids = fields.Many2many('hr.employee', 'cand_int2_rel', 'cand_id', 'emp_id', string='Round 2 Interviewers')
    interview2_hr_interviewer_id = fields.Many2one('hr.employee', string='Round 2 HR Interviewer')
    interview2_google_meet_link = fields.Char('Round 2 Google Meet Link')
    interview2_result = fields.Selection(INTERVIEW_RESULTS, string='Round 2 Result')
    interview2_feedback = fields.Text('Round 2 Feedback')
    interview2_remarks = fields.Text('Round 2 Remarks')

    interview3_date = fields.Date('Round 3 Date')
    interview3_interviewer_ids = fields.Many2many('hr.employee', 'cand_int3_rel', 'cand_id', 'emp_id', string='Round 3 Interviewers')
    interview3_hr_interviewer_id = fields.Many2one('hr.employee', string='Round 3 HR Interviewer')
    interview3_google_meet_link = fields.Char('Round 3 Google Meet Link')
    interview3_result = fields.Selection(INTERVIEW_RESULTS, string='Round 3 Result')
    interview3_feedback = fields.Text('Round 3 Feedback')
    interview3_remarks = fields.Text('Round 3 Remarks')

    # Assessment
    assessment_done = fields.Boolean('Assessment Done')
    assessment_date = fields.Date('Assessment Date')
    assessment_result = fields.Selection(ASSESSMENT_RESULTS, string='Assessment Result', default='pending')
    assessment_remarks = fields.Text('Assessment Remarks')

    # Offer details
    offer_prepared_by = fields.Many2one('hr.employee', string='Offer Prepared By')
    offer_prepared_date = fields.Date('Offer Prepared Date')
    offer_released_date = fields.Date('Offer Released Date')
    offer_accepted_date = fields.Date('Offer Accepted Date')
    current_ctc = fields.Monetary('Current CTC', currency_field='offer_currency_id')
    offered_ctc = fields.Monetary('Offered CTC', currency_field='offer_currency_id')
    offer_currency_id = fields.Many2one('res.currency', string='Offer Currency',
                                        default=lambda self: self.env.company.currency_id)

    # Pre-joining compliance
    documents_received_date = fields.Date('Documents Received Date')
    bgv_initiated_date = fields.Date('BGV Initiated Date')
    bgv_completed_date = fields.Date('BGV Completed Date')
    bgv_status = fields.Selection([
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('clear', 'Clear'),
        ('discrepancy', 'Discrepancy'),
        ('waived', 'Waived'),
    ], string='BGV Status', default='pending')
    bgv_remarks = fields.Text('BGV Remarks')

    medical_clearance_date = fields.Date('Medical Clearance Date')
    medical_status = fields.Selection([
        ('pending', 'Pending'),
        ('fit', 'Fit'),
        ('conditional', 'Conditional Fit'),
        ('unfit', 'Unfit'),
    ], string='Medical Status', default='pending')

    visa_type = fields.Selection([
        ('pec', 'PEC'),
        ('vvl', 'VVL'),
        ('not_required', 'Travel Not Required'),
        ('business', 'Business Visa'),
        ('work_permit', 'Work Permit'),
    ], string='Visa Type')
    pec_initiated_date = fields.Date('PEC Initiated Date')
    visa_received_date = fields.Date('Visa Received Date')

    expected_doj = fields.Date('Expected Date of Joining')
    actual_doj = fields.Date('Actual Date of Joining')

    bank_details_updated = fields.Boolean('Bank Details Updated')
    joining_circular_dispatched = fields.Boolean('Joining Circular Dispatched')
    joining_circular_date = fields.Date('Joining Circular Date')
    online_onboarding_completed = fields.Boolean('Online Onboarding Completed')

    # Offer drop
    drop_ids = fields.One2many('vmf.candidate.drop', 'candidate_id', string='Offer Drop Log')
    is_dropped = fields.Boolean('Dropped', compute='_compute_is_dropped', store=True)

    # Hold
    hold_ids = fields.One2many('vmf.candidate.hold', 'candidate_id', string='Hold Log')

    # Created employee
    employee_id = fields.Many2one('hr.employee', string='Employee Created', readonly=True)

    # Computed TAT
    tat_days = fields.Integer('TAT (days)', compute='_compute_tat', store=False)

    # Notes
    notes = fields.Text('Notes')

    # Documents
    candidate_document_ids = fields.Many2many('ir.attachment', 'cand_doc_rel', 'cand_id', 'attach_id', string='Documents')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.candidate_name} - {rec.name}" if rec.name else rec.candidate_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.candidate') or 'New'
            if vals.get('mrf_id'):
                mrf = self.env['vmf.mrf'].browse(vals['mrf_id'])
                if mrf:
                    if not vals.get('hiring_manager_id'):
                        vals['hiring_manager_id'] = mrf.hiring_manager_id.id
                    if not vals.get('coordinator_id'):
                        vals['coordinator_id'] = mrf.coordinator_id.id
        return super().create(vals_list)

    @api.onchange('mrf_id')
    def _onchange_mrf_id_populate_recruitment_team(self):
        if self.mrf_id:
            self.hiring_manager_id = self.mrf_id.hiring_manager_id
            self.coordinator_id = self.mrf_id.coordinator_id

    @api.depends('drop_ids')
    def _compute_is_dropped(self):
        for rec in self:
            rec.is_dropped = bool(rec.drop_ids.filtered(lambda d: not d.reinstated))

    def _compute_tat(self):
        today = date.today()
        for rec in self:
            start = rec.resume_received_date or rec.create_date.date()
            if rec.actual_doj:
                rec.tat_days = (rec.actual_doj - start).days
            else:
                rec.tat_days = (today - start).days

    def action_move_to_screening(self):
        self.write({'state': 'screening'})

    def action_open_invitation_wizard(self):
        self.ensure_one()
        round_map = {
            'screening': '1',
            'interview_1': '2',
            'interview_2': '3',
        }
        round_no = round_map.get(self.state)
        if not round_no:
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Interview Invitation'),
            'res_model': 'vmf.candidate.invitation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_candidate_id': self.id,
                'default_round_number': round_no,
            }
        }

    def action_open_feedback_wizard(self):
        self.ensure_one()
        round_map = {
            'interview_1': '1',
            'interview_2': '2',
            'interview_3': '3',
        }
        round_no = round_map.get(self.state)
        if not round_no:
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interview Feedback'),
            'res_model': 'vmf.candidate.feedback.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_candidate_id': self.id,
                'default_round_number': round_no,
            }
        }

    def action_schedule_interview1(self):
        self.write({'state': 'interview_1'})

    def action_schedule_interview2(self):
        self.write({'state': 'interview_2'})

    def action_schedule_interview3(self):
        self.write({'state': 'interview_3'})

    def _action_open_calendar_event(self, meeting_name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Interview'),
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f"{meeting_name}: {self.candidate_name}",
                'default_description': f"Interview for {self.job_id.name} ({self.name})",
                'default_partner_ids': [self.env.user.partner_id.id],
            }
        }

    def action_select(self):
        self.write({'state': 'selected'})
        self.message_post(body=_('Candidate selected.'))

    def action_prepare_offer(self):
        self.write({'state': 'offer_prepared', 'offer_prepared_date': date.today()})

    def action_release_offer(self):
        self.write({'state': 'offer_released', 'offer_released_date': date.today()})
        self.message_post(body=_('Offer letter released to candidate.'))

    def action_accept_offer(self):
        self.write({'state': 'offer_accepted', 'offer_accepted_date': date.today()})

    def action_bgv(self):
        self.write({'state': 'bgv', 'bgv_initiated_date': date.today()})

    def action_confirm_joining(self):
        self.write({'state': 'joining_confirmed'})

    def action_mark_joined(self):
        self.write({'state': 'joined', 'actual_doj': date.today()})
        self.message_post(body=_('Candidate joined. Please create employee record.'))

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_create_employee(self):
        """Convert candidate to employee record"""
        self.ensure_one()
        if self.employee_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'res_id': self.employee_id.id,
                'view_mode': 'form',
            }
        employee_vals = {
            'name': self.candidate_name,
            'work_email': self.email,
            'mobile_phone': self.mobile,
            'department_id': self.department_id.id,
            'job_id': self.job_id.id,
            'company_id': self.company_id.id,
            'vmf_grade_id': self.grade_id.id,
            'vmf_employee_category': self.mrf_id.employee_category,
        }
        employee = self.env['hr.employee'].create(employee_vals)
        self.write({'employee_id': employee.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
        }

    def action_print_offer_letter(self):
        return self.env.ref('vmf_hrms.action_report_offer_letter').report_action(self)


class VmfCandidateDrop(models.Model):
    _name = 'vmf.candidate.drop'
    _description = 'Offer Drop Log'
    _order = 'drop_date desc'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, ondelete='cascade')
    drop_date = fields.Date('Drop Date', required=True, default=fields.Date.today)
    drop_stage = fields.Selection([
        ('after_ol', 'After Offer Letter'),
        ('no_show', 'No Show on Joining'),
        ('during_notice', 'Dropped During Notice Period'),
        ('before_bgv', 'Before BGV Completion'),
        ('visa_rejected', 'Visa Rejected'),
    ], string='Drop Stage', required=True)
    drop_reason = fields.Text('Drop Reason', required=True)
    previous_state = fields.Selection([
        ('new', 'New'),
        ('screening', 'Screening'),
        ('interview_1', 'Interview 1'),
        ('interview_2', 'Interview 2'),
        ('interview_3', 'Interview 3'),
        ('selected', 'Selected'),
        ('offer_prepared', 'Offer Prepared'),
        ('offer_released', 'Offer Released'),
        ('offer_accepted', 'Offer Accepted'),
        ('bgv', 'BGV / Medical / Visa'),
        ('joining_confirmed', 'Joining Confirmed'),
        ('joined', 'Joined'),
        ('offer_dropped', 'Offer Dropped'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ], string='Previous Status')
    days_lost = fields.Integer('Days Lost', compute='_compute_days_lost', store=True)
    reinstated = fields.Boolean('Reinstated / Reconsidered')
    notes = fields.Text('Notes')

    @api.depends('drop_date', 'candidate_id.resume_received_date')
    def _compute_days_lost(self):
        for rec in self:
            if rec.drop_date and rec.candidate_id.resume_received_date:
                rec.days_lost = (rec.drop_date - rec.candidate_id.resume_received_date).days
            else:
                rec.days_lost = 0


class VmfCandidateHold(models.Model):
    _name = 'vmf.candidate.hold'
    _description = 'Candidate Hold Log'
    _order = 'hold_start desc'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, ondelete='cascade')
    hold_start = fields.Date('Hold Start', required=True, default=fields.Date.today)
    hold_end = fields.Date('Hold End')
    hold_reason = fields.Text('Hold Reason', required=True)
    reopen_reason = fields.Text('Reopen Reason')
    previous_state = fields.Selection([
        ('new', 'New'),
        ('screening', 'Screening'),
        ('interview_1', 'Interview 1'),
        ('interview_2', 'Interview 2'),
        ('interview_3', 'Interview 3'),
        ('selected', 'Selected'),
        ('offer_prepared', 'Offer Prepared'),
        ('offer_released', 'Offer Released'),
        ('offer_accepted', 'Offer Accepted'),
        ('bgv', 'BGV / Medical / Visa'),
        ('joining_confirmed', 'Joining Confirmed'),
        ('joined', 'Joined'),
        ('offer_dropped', 'Offer Dropped'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ], string='Previous Status')
    hold_days = fields.Integer('Hold Days', compute='_compute_hold_days', store=True)

    @api.depends('hold_start', 'hold_end')
    def _compute_hold_days(self):
        for rec in self:
            if rec.hold_start and rec.hold_end:
                rec.hold_days = (rec.hold_end - rec.hold_start).days
            else:
                rec.hold_days = 0
