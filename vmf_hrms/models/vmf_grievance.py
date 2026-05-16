from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import date, timedelta


class VmfGrievance(models.Model):
    _name = 'vmf.grievance'
    _description = 'Grievance Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char('Grievance No.', readonly=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)

    is_anonymous = fields.Boolean('Anonymous / Confidential', default=False)
    grievance_type = fields.Selection([
        ('workplace_conduct', 'Workplace Conduct'),
        ('harassment', 'Harassment / Discrimination'),
        ('compensation', 'Compensation / Benefits'),
        ('working_conditions', 'Working Conditions'),
        ('policy_violation', 'Policy Violation'),
        ('management_conduct', 'Management Conduct'),
        ('safety', 'Safety Concern'),
        ('other', 'Other'),
    ], string='Grievance Type', required=True)

    subject = fields.Char('Subject', required=True)
    description = fields.Text('Grievance Description', required=True)
    date_filed = fields.Date('Date Filed', default=fields.Date.today, readonly=True)
    parties_involved = fields.Text('Parties Involved')

    state = fields.Selection([
        ('open', 'Open'),
        ('under_investigation', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
        ('closed', 'Closed'),
        ('withdrawn', 'Withdrawn'),
    ], string='Status', default='open', tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Priority', default='medium')

    case_owner_id = fields.Many2one('hr.employee', string='Case Owner / Investigator', tracking=True)
    sla_days = fields.Integer('SLA (working days)', default=15)
    sla_due_date = fields.Date('SLA Due Date', compute='_compute_sla', store=True)
    sla_breached = fields.Boolean('SLA Breached', compute='_compute_sla_breach', store=False)

    investigation_notes = fields.Text('Investigation Notes')
    resolution = fields.Text('Resolution / Decision')
    resolution_date = fields.Date('Resolution Date')
    employee_acknowledged = fields.Boolean('Employee Acknowledged Resolution')
    acknowledgement_date = fields.Date('Acknowledgement Date')

    escalated_to_id = fields.Many2one('hr.employee', string='Escalated To')
    escalation_reason = fields.Text('Escalation Reason')

    notes = fields.Text('Internal Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.grievance') or 'New'
        return super().create(vals_list)

    @api.depends('date_filed', 'sla_days')
    def _compute_sla(self):
        for rec in self:
            if rec.date_filed and rec.sla_days:
                rec.sla_due_date = rec.date_filed + timedelta(days=rec.sla_days)
            else:
                rec.sla_due_date = False

    def _compute_sla_breach(self):
        today = date.today()
        for rec in self:
            if rec.sla_due_date and rec.state not in ('resolved', 'closed', 'withdrawn'):
                rec.sla_breached = today > rec.sla_due_date
            else:
                rec.sla_breached = False

    def action_investigate(self):
        self.write({'state': 'under_investigation'})
        self.message_post(body=_('Investigation started by %s.') % (self.case_owner_id.name or 'HR'))

    def action_resolve(self):
        self.write({'state': 'resolved', 'resolution_date': date.today()})
        self.message_post(body=_('Grievance resolved. Awaiting employee acknowledgement.'))

    def action_escalate(self):
        self.write({'state': 'escalated'})

    def action_employee_acknowledge(self):
        self.write({
            'state': 'closed',
            'employee_acknowledged': True,
            'acknowledgement_date': date.today(),
        })
        self.message_post(body=_('Employee acknowledged resolution. Case closed.'))

    def action_withdraw(self):
        self.write({'state': 'withdrawn'})
        self.message_post(body=_('Grievance withdrawn by employee.'))


class VmfPulseSurveySchedule(models.Model):
    _name = 'vmf.pulse.survey'
    _description = '30-60-90 Day Onboarding Survey Schedule'
    _order = 'scheduled_date'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    survey_type = fields.Selection([
        ('day30', '30-Day Check-in'),
        ('day60', '60-Day Check-in'),
        ('day90', '90-Day Check-in'),
        ('annual_engagement', 'Annual Engagement Survey'),
        ('exit', 'Exit Survey'),
        ('pulse', 'Pulse Survey'),
    ], string='Survey Type', required=True)
    scheduled_date = fields.Date('Scheduled Date', required=True)
    survey_id = fields.Many2one('survey.survey', string='Survey Form')
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ], default='scheduled')
    completion_date = fields.Date('Completion Date')
    response_id = fields.Many2one('survey.user_input', string='Response')
    notes = fields.Text('Notes')

    def action_send_survey(self):
        self.write({'state': 'sent'})

    def action_mark_completed(self):
        self.write({'state': 'completed', 'completion_date': date.today()})
