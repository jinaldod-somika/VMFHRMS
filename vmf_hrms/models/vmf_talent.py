from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from datetime import date


COMPETENCY_LEVELS = [
    ('1', '1 — Beginner'),
    ('2', '2 — Working Knowledge'),
    ('3', '3 — Practitioner'),
    ('4', '4 — Advanced'),
    ('5', '5 — Expert'),
]


class VmfCompetency(models.Model):
    _name = 'vmf.competency'
    _description = 'Competency'
    _order = 'category, name'

    name = fields.Char('Competency Name', required=True)
    code = fields.Char('Code')
    category = fields.Selection([
        ('technical', 'Technical / Functional'),
        ('behavioral', 'Behavioral'),
        ('leadership', 'Leadership'),
        ('digital', 'Digital'),
        ('safety', 'Safety / EHS'),
    ], string='Category', required=True, default='technical')
    description = fields.Text('Description')
    skill_id = fields.Many2one('hr.skill', string='Linked Skill',
        help='Optional link to the standard Odoo skill catalog.')
    active = fields.Boolean('Active', default=True)


class VmfCompetencyMatrix(models.Model):
    _name = 'vmf.competency.matrix'
    _description = 'Competency Matrix (Required Levels)'
    _order = 'grade_id, job_id, competency_id'
    _rec_name = 'display_name'

    display_name = fields.Char('Reference', compute='_compute_display_name', store=True)
    grade_id = fields.Many2one('vmf.grade', string='Grade')
    job_id = fields.Many2one('hr.job', string='Job Position')
    competency_id = fields.Many2one('vmf.competency', string='Competency', required=True)
    required_level = fields.Selection(COMPETENCY_LEVELS, string='Required Level',
        required=True, default='3')
    is_critical = fields.Boolean('Critical Competency',
        help='Critical competencies are weighted higher in skill-gap analysis.')
    notes = fields.Text('Notes')

    @api.depends('grade_id', 'job_id', 'competency_id')
    def _compute_display_name(self):
        for rec in self:
            scope = rec.job_id.name if rec.job_id else (rec.grade_id.name if rec.grade_id else 'All')
            comp = rec.competency_id.name if rec.competency_id else ''
            rec.display_name = f"{scope} → {comp}"

    @api.constrains('grade_id', 'job_id')
    def _check_scope(self):
        for rec in self:
            if not rec.grade_id and not rec.job_id:
                raise ValidationError(_('Provide at least Grade or Job Position to scope this competency requirement.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('grade_id') and not vals.get('job_id'):
                raise ValidationError(_('Provide at least Grade or Job Position to scope this competency requirement.'))
        return super().create(vals_list)


class VmfIDP(models.Model):
    _name = 'vmf.idp'
    _description = 'Individual Development Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'period_start desc'

    name = fields.Char('IDP Reference', readonly=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    grade_id = fields.Many2one('vmf.grade', related='employee_id.vmf_grade_id', store=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', store=True)

    period_start = fields.Date('Plan Start', default=fields.Date.today, required=True, tracking=True)
    period_end = fields.Date('Plan End', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('agreed', 'Agreed with Employee'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    aspiration = fields.Text('Career Aspiration / Next Role',
        help='Where the employee wants to be in the next 12-24 months.')
    strengths_summary = fields.Text('Strengths Summary')
    development_focus = fields.Text('Development Focus Areas')
    review_id = fields.Many2one('vmf.performance.review', string='Linked Performance Review')
    talent_review_id = fields.Many2one('vmf.talent.review', string='Linked Talent Review')

    action_line_ids = fields.One2many('vmf.idp.action', 'idp_id', string='Development Actions')
    overall_progress = fields.Float('Overall Progress (%)',
        compute='_compute_overall_progress', store=True)

    @api.depends('action_line_ids.status')
    def _compute_overall_progress(self):
        for rec in self:
            actions = rec.action_line_ids
            if not actions:
                rec.overall_progress = 0.0
            else:
                completed = len(actions.filtered(lambda a: a.status == 'completed'))
                rec.overall_progress = (completed / len(actions)) * 100

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.idp') or 'New'
        return super().create(vals_list)

    def action_agree(self):
        self.write({'state': 'agreed'})
        self.message_post(body=_('IDP agreed with employee.'))

    def action_activate(self):
        self.write({'state': 'active'})

    def action_complete(self):
        self.write({'state': 'completed'})
        self.message_post(body=_('IDP marked as completed.'))

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class VmfIDPAction(models.Model):
    _name = 'vmf.idp.action'
    _description = 'IDP Development Action'
    _order = 'sequence, target_date'

    idp_id = fields.Many2one('vmf.idp', string='IDP', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='idp_id.employee_id', store=True)
    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Development Action', required=True)
    competency_id = fields.Many2one('vmf.competency', string='Competency')
    current_level = fields.Selection(COMPETENCY_LEVELS, string='Current Level')
    target_level = fields.Selection(COMPETENCY_LEVELS, string='Target Level')
    action_type = fields.Selection([
        ('course', 'Training Course'),
        ('on_job', 'On-the-Job Practice'),
        ('mentoring', 'Mentoring'),
        ('coaching', 'Coaching'),
        ('project', 'Stretch Assignment / Project'),
        ('reading', 'Reading / Self-Study'),
        ('certification', 'Certification'),
        ('other', 'Other'),
    ], string='Action Type', required=True, default='course')
    course_id = fields.Many2one('vmf.course', string='Course',
        help='Linked course (auto-creates a course assignment when IDP is activated).')
    course_assignment_ids = fields.One2many('vmf.course.assignment', 'idp_action_id',
        string='Course Assignments')
    target_date = fields.Date('Target Completion Date')
    completion_date = fields.Date('Completion Date')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending')
    notes = fields.Text('Notes')

    def action_create_course_assignment(self):
        self.ensure_one()
        if not self.course_id:
            raise ValidationError(_('Please select a course before creating the assignment.'))
        return self.env['vmf.course.assignment'].create({
            'employee_id': self.idp_id.employee_id.id,
            'course_id': self.course_id.id,
            'idp_action_id': self.id,
            'target_completion_date': self.target_date,
        })


class VmfTalentReview(models.Model):
    _name = 'vmf.talent.review'
    _description = 'Talent Review (9-Box)'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'review_year desc, employee_id'

    name = fields.Char('Reference', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    grade_id = fields.Many2one('vmf.grade', related='employee_id.vmf_grade_id', store=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', store=True)

    review_year = fields.Integer('Review Year', default=lambda self: date.today().year, required=True)
    review_date = fields.Date('Review Date', default=fields.Date.today)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By',
        default=lambda self: self.env.user)

    performance_rating = fields.Selection([
        ('1', '1 — Low'),
        ('2', '2 — Medium'),
        ('3', '3 — High'),
    ], string='Performance', required=True, default='2', tracking=True)
    potential_rating = fields.Selection([
        ('1', '1 — Low'),
        ('2', '2 — Medium'),
        ('3', '3 — High'),
    ], string='Potential', required=True, default='2', tracking=True)
    nine_box_position = fields.Selection([
        ('1', '1 — Underperformer'),
        ('2', '2 — Effective'),
        ('3', '3 — Trusted Professional'),
        ('4', '4 — Inconsistent Player'),
        ('5', '5 — Core Player'),
        ('6', '6 — High Performer'),
        ('7', '7 — Enigma'),
        ('8', '8 — Growth Employee'),
        ('9', '9 — Star / HIPO'),
    ], string='9-Box Position', compute='_compute_nine_box', store=True)

    is_hipo = fields.Boolean('HIPO', compute='_compute_is_hipo', store=True, tracking=True,
        help='Auto-flagged for box 8 (Growth) and box 9 (Star).')
    retention_risk = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Retention Risk', default='low', tracking=True)
    impact_of_loss = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Impact of Loss', default='medium')

    recommended_actions = fields.Text('Recommended Actions')
    successor_for_role_ids = fields.Many2many('hr.job',
        'vmf_talent_review_successor_role_rel', 'review_id', 'job_id',
        string='Identified as Successor For')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Review'),
        ('calibrated', 'Calibrated'),
        ('active', 'Active / Confirmed'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('employee_id', 'review_year')
    def _compute_name(self):
        for rec in self:
            emp = rec.employee_id.name if rec.employee_id else 'Unknown'
            rec.name = f"TALENT/{emp}/{rec.review_year}"

    @api.depends('performance_rating', 'potential_rating')
    def _compute_nine_box(self):
        # 9-box grid:
        #   Potential→        Low(1)      Medium(2)      High(3)
        #   Performance High:    3           6              9
        #   Performance Med:     2           5              8
        #   Performance Low:     1           4              7
        mapping = {
            ('1', '1'): '1', ('1', '2'): '4', ('1', '3'): '7',
            ('2', '1'): '2', ('2', '2'): '5', ('2', '3'): '8',
            ('3', '1'): '3', ('3', '2'): '6', ('3', '3'): '9',
        }
        for rec in self:
            key = (rec.performance_rating or '2', rec.potential_rating or '2')
            rec.nine_box_position = mapping.get(key, '5')

    @api.depends('nine_box_position')
    def _compute_is_hipo(self):
        for rec in self:
            rec.is_hipo = rec.nine_box_position in ('8', '9')

    def action_submit(self):
        self.write({'state': 'submitted'})
        self._notify_talent_review(_('Talent review submitted for calibration.'))

    def action_calibrate(self):
        self.write({'state': 'calibrated'})

    def action_confirm(self):
        self.write({'state': 'active'})
        self._notify_talent_review(_('Talent review confirmed and finalized.'))

    def _notify_talent_review(self, message_prefix):
        for rec in self:
            rec.message_post(body=f"<b>{message_prefix}</b><br/>Employee: {rec.employee_id.name}<br/>Review Year: {rec.review_year}")
            # Notify Manager
            if rec.employee_id.parent_id and rec.employee_id.parent_id.user_id:
                rec.message_post(body=f"Talent Notification: {rec.name} updated.", partner_ids=[rec.employee_id.parent_id.user_id.partner_id.id])
            # Notify HR Coach
            if rec.employee_id.vmf_business_hr_id and rec.employee_id.vmf_business_hr_id.user_id:
                rec.message_post(body=f"Talent Notification: {rec.name} updated.", partner_ids=[rec.employee_id.vmf_business_hr_id.user_id.partner_id.id])


class VmfSuccessionPlan(models.Model):
    _name = 'vmf.succession.plan'
    _description = 'Succession Plan'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'critical_role_id'

    name = fields.Char('Reference', compute='_compute_name', store=True)
    critical_role_id = fields.Many2one('hr.job', string='Critical Role',
        required=True, tracking=True,
        help='Critical role for which a successor pipeline is being built.')
    incumbent_id = fields.Many2one('hr.employee', string='Current Incumbent', tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', related='critical_role_id.department_id', store=True)
    grade_id = fields.Many2one('vmf.grade', related='critical_role_id.grade_id', store=True)
    is_critical_role = fields.Boolean(related='critical_role_id.is_critical_role',
        store=True, string='Critical Role Flag')

    successor_line_ids = fields.One2many('vmf.successor.line', 'succession_plan_id',
        string='Successors')
    successor_count = fields.Integer('Successor Count',
        compute='_compute_successor_count', store=True)
    ready_now_count = fields.Integer('Ready Now',
        compute='_compute_successor_count', store=True)

    review_year = fields.Integer('Review Year', default=lambda self: date.today().year)
    last_reviewed = fields.Date('Last Reviewed', default=fields.Date.today)
    idp_id = fields.Many2one('vmf.idp', string='Linked IDP', help='Individual Development Plan for the successor pool.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text('Notes')

    @api.depends('critical_role_id', 'incumbent_id')
    def _compute_name(self):
        for rec in self:
            role = rec.critical_role_id.name if rec.critical_role_id else 'Role'
            inc = f" — {rec.incumbent_id.name}" if rec.incumbent_id else ''
            rec.name = f"SUCC/{role}{inc}"

    @api.depends('successor_line_ids', 'successor_line_ids.readiness')
    def _compute_successor_count(self):
        for rec in self:
            rec.successor_count = len(rec.successor_line_ids)
            rec.ready_now_count = len(rec.successor_line_ids.filtered(
                lambda s: s.readiness == 'now'))

    def action_activate(self):
        self.write({'state': 'active'})

    def action_archive_plan(self):
        self.write({'state': 'archived'})


class VmfSuccessorLine(models.Model):
    _name = 'vmf.successor.line'
    _description = 'Successor Candidate'
    _order = 'sequence, readiness'

    succession_plan_id = fields.Many2one('vmf.succession.plan', string='Succession Plan',
        required=True, ondelete='cascade')
    sequence = fields.Integer('Rank', default=10)
    candidate_id = fields.Many2one('hr.employee', string='Successor', required=True)
    current_role = fields.Char(related='candidate_id.job_title', string='Current Role')
    grade_id = fields.Many2one('vmf.grade', related='candidate_id.vmf_grade_id',
        store=True, string='Current Grade')
    readiness = fields.Selection([
        ('now', 'Ready Now'),
        ('1_2_year', 'Ready in 1-2 Years'),
        ('2_3_year', 'Ready in 2-3 Years'),
        ('not_ready', 'Not Ready / Watch'),
    ], string='Readiness', required=True, default='1_2_year')
    is_hipo = fields.Boolean('HIPO',
        compute='_compute_is_hipo', store=True)
    development_actions = fields.Text('Development Actions')
    notes = fields.Text('Notes')

    @api.depends('candidate_id')
    def _compute_is_hipo(self):
        for rec in self:
            latest = self.env['vmf.talent.review'].search([
                ('employee_id', '=', rec.candidate_id.id),
            ], order='review_year desc', limit=1)
            rec.is_hipo = latest.is_hipo if latest else False


class VmfHrEmployeeTalent(models.Model):
    """Talent fields on the employee record."""
    _inherit = 'hr.employee'

    idp_ids = fields.One2many('vmf.idp', 'employee_id', string='IDPs')
    talent_review_ids = fields.One2many('vmf.talent.review', 'employee_id', string='Talent Reviews')
    is_hipo = fields.Boolean('HIPO', compute='_compute_is_hipo_employee', store=True,
        help='Auto-set from latest confirmed talent review.')
    idp_active_count = fields.Integer('Active IDPs', compute='_compute_idp_active_count')

    @api.depends('talent_review_ids.is_hipo', 'talent_review_ids.review_year')
    def _compute_is_hipo_employee(self):
        for rec in self:
            latest = rec.talent_review_ids.sorted(lambda r: r.review_year, reverse=True)[:1]
            rec.is_hipo = bool(latest and latest.is_hipo)

    @api.depends('idp_ids.state')
    def _compute_idp_active_count(self):
        for rec in self:
            rec.idp_active_count = len(rec.idp_ids.filtered(lambda i: i.state == 'active'))

    def action_view_idp(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Individual Development Plans'),
            'res_model': 'vmf.idp',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_talent_reviews(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Talent Reviews'),
            'res_model': 'vmf.talent.review',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_compute_skill_gap(self):
        """Generate / refresh skill gap assessment for the employee against the competency matrix."""
        self.ensure_one()
        SkillGap = self.env['vmf.skill.gap']
        SkillGap.search([('employee_id', '=', self.id)]).unlink()
        matrix_rows = self.env['vmf.competency.matrix']
        if self.vmf_grade_id:
            matrix_rows |= matrix_rows.search([('grade_id', '=', self.vmf_grade_id.id)])
        if self.job_id:
            matrix_rows |= matrix_rows.search([('job_id', '=', self.job_id.id)])
        for row in matrix_rows:
            SkillGap.create({
                'employee_id': self.id,
                'competency_id': row.competency_id.id,
                'required_level': row.required_level,
                'is_critical': row.is_critical,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Skill Gap'),
            'res_model': 'vmf.skill.gap',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
        }


class VmfSkillGap(models.Model):
    _name = 'vmf.skill.gap'
    _description = 'Skill Gap Assessment'
    _order = 'employee_id, competency_id'
    _rec_name = 'competency_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    competency_id = fields.Many2one('vmf.competency', string='Competency', required=True)
    required_level = fields.Selection(COMPETENCY_LEVELS, string='Required Level', required=True)
    current_level = fields.Selection(COMPETENCY_LEVELS, string='Current Level', default='1')
    gap = fields.Integer('Gap (levels)', compute='_compute_gap', store=True)
    is_critical = fields.Boolean('Critical Competency')
    recommended_action = fields.Text('Recommended Action')
    assessment_date = fields.Date('Assessed On', default=fields.Date.today)
    state = fields.Selection([
        ('draft', 'To be Assessed'),
        ('assessed', 'Assessed'),
        ('verified', 'Verified'),
    ], string='Status', default='draft', tracking=True)

    def action_assess(self):
        self.write({'state': 'assessed', 'assessment_date': fields.Date.today()})

    def action_verify(self):
        self.write({'state': 'verified'})

    @api.depends('required_level', 'current_level')
    def _compute_gap(self):
        for rec in self:
            req = int(rec.required_level or '0')
            curr = int(rec.current_level or '0')
            rec.gap = max(0, req - curr)
