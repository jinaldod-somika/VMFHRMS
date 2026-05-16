from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class VmfCourse(models.Model):
    _name = 'vmf.course'
    _description = 'Learning Course'
    _inherit = ['mail.thread']
    _order = 'category, name'

    name = fields.Char('Course Name', required=True, tracking=True)
    code = fields.Char('Course Code', readonly=True, copy=False, default='New')
    description = fields.Html('Description')
    category = fields.Selection([
        ('technical', 'Technical / Functional'),
        ('behavioral', 'Behavioral / Soft Skills'),
        ('leadership', 'Leadership'),
        ('compliance', 'Compliance / Statutory'),
        ('safety', 'Safety / EHS'),
        ('induction', 'Induction / Onboarding'),
    ], string='Category', required=True, default='technical', tracking=True)
    delivery_mode = fields.Selection([
        ('classroom', 'Classroom / Instructor-Led'),
        ('elearning', 'E-Learning / Self-Paced'),
        ('blended', 'Blended (Classroom + E-Learning)'),
        ('on_job', 'On-the-Job'),
        ('webinar', 'Webinar / Virtual'),
        ('mentoring', 'Mentoring / Coaching'),
    ], string='Delivery Mode', required=True, default='elearning')
    duration_hours = fields.Float('Duration (hours)', default=8.0)
    provider_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External Vendor'),
    ], string='Provider Type', default='internal')
    provider_name = fields.Char('Provider / Vendor')
    cost_per_seat = fields.Float('Cost per Seat')
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
    skill_ids = fields.Many2many('hr.skill', string='Skills Imparted',
        help='Skills the participant develops on completing this course.')
    grade_ids = fields.Many2many('vmf.grade', 'vmf_course_grade_rel',
        'course_id', 'grade_id', string='Applicable Grades')
    job_ids = fields.Many2many('hr.job', 'vmf_course_job_rel',
        'course_id', 'job_id', string='Applicable Job Positions')
    is_mandatory = fields.Boolean('Mandatory',
        help='If checked, this course must be completed by all employees in the applicable scope.')
    validity_months = fields.Integer('Validity (months)', default=0,
        help='Re-certification interval. 0 = no expiry.')
    pre_requisite_ids = fields.Many2many('vmf.course', 'vmf_course_prereq_rel',
        'course_id', 'prereq_id', string='Pre-Requisite Courses')
    active = fields.Boolean('Active', default=True)

    assignment_count = fields.Integer('Assignments', compute='_compute_assignment_count')

    @api.depends('code')
    def _compute_assignment_count(self):
        for rec in self:
            rec.assignment_count = self.env['vmf.course.assignment'].search_count([('course_id', '=', rec.id)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('vmf.course') or 'New'
        return super().create(vals_list)

    def action_view_assignments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Assignments'),
            'res_model': 'vmf.course.assignment',
            'view_mode': 'list,form,kanban',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id},
        }


class VmfLearningPath(models.Model):
    _name = 'vmf.learning.path'
    _description = 'Learning Path'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char('Learning Path Name', required=True, tracking=True)
    code = fields.Char('Path Code', readonly=True, copy=False, default='New')
    description = fields.Html('Description')
    target_grade_id = fields.Many2one('vmf.grade', string='Target Grade')
    target_job_id = fields.Many2one('hr.job', string='Target Job Position')
    target_audience = fields.Selection([
        ('all', 'All Employees'),
        ('new_joiner', 'New Joiners'),
        ('hipo', 'HIPO Employees'),
        ('successor', 'Successors'),
        ('grade', 'Specific Grade'),
        ('job', 'Specific Job Position'),
    ], string='Target Audience', default='all')
    course_line_ids = fields.One2many('vmf.learning.path.line', 'learning_path_id', string='Courses')
    total_duration_hours = fields.Float('Total Duration (hours)',
        compute='_compute_total_duration', store=True)
    total_cost = fields.Float('Total Cost',
        compute='_compute_total_cost', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
    active = fields.Boolean('Active', default=True)

    @api.depends('course_line_ids.course_id.duration_hours')
    def _compute_total_duration(self):
        for rec in self:
            rec.total_duration_hours = sum(line.course_id.duration_hours for line in rec.course_line_ids)

    @api.depends('course_line_ids.course_id.cost_per_seat')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(line.course_id.cost_per_seat for line in rec.course_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('vmf.learning.path') or 'New'
        return super().create(vals_list)


class VmfLearningPathLine(models.Model):
    _name = 'vmf.learning.path.line'
    _description = 'Learning Path Course Line'
    _order = 'sequence, id'

    learning_path_id = fields.Many2one('vmf.learning.path', string='Learning Path',
        required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    course_id = fields.Many2one('vmf.course', string='Course', required=True)
    is_required = fields.Boolean('Required', default=True)
    duration_hours = fields.Float(related='course_id.duration_hours', string='Duration')
    category = fields.Selection(related='course_id.category', string='Category')


class VmfCourseAssignment(models.Model):
    _name = 'vmf.course.assignment'
    _description = 'Course Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'target_completion_date'

    name = fields.Char('Reference', readonly=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    course_id = fields.Many2one('vmf.course', string='Course', required=True, tracking=True)
    course_category = fields.Selection(related='course_id.category', store=True)
    learning_path_id = fields.Many2one('vmf.learning.path', string='Learning Path')
    idp_action_id = fields.Many2one('vmf.idp.action', string='IDP Action',
        help='Course assigned as part of an Individual Development Plan action.')
    assigned_by = fields.Many2one('res.users', string='Assigned By',
        default=lambda self: self.env.user, tracking=True)
    assignment_date = fields.Date('Assignment Date', default=fields.Date.today, tracking=True)
    target_completion_date = fields.Date('Target Completion Date', tracking=True)
    actual_completion_date = fields.Date('Actual Completion Date', tracking=True)
    state = fields.Selection([
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='assigned', tracking=True)
    score = fields.Float('Score / Percentage')
    pass_mark = fields.Float('Pass Mark', default=60.0)
    is_passed = fields.Boolean('Passed', compute='_compute_is_passed', store=True)
    effectiveness_rating = fields.Selection([
        ('1', '1 — Very Poor'),
        ('2', '2 — Poor'),
        ('3', '3 — Average'),
        ('4', '4 — Good'),
        ('5', '5 — Excellent'),
    ], string='Effectiveness Rating',
        help='Manager assessment of the impact of the training on the job.')
    feedback_employee = fields.Text('Employee Feedback')
    feedback_manager = fields.Text('Manager Feedback')
    certificate_attachment_id = fields.Many2one('ir.attachment', string='Certificate')
    days_to_target = fields.Integer('Days to Target', compute='_compute_days_to_target')

    @api.depends('score', 'pass_mark', 'state')
    def _compute_is_passed(self):
        for rec in self:
            rec.is_passed = bool(rec.state == 'completed' and rec.score and rec.score >= rec.pass_mark)

    @api.depends('target_completion_date')
    def _compute_days_to_target(self):
        today = fields.Date.today()
        for rec in self:
            if rec.target_completion_date:
                rec.days_to_target = (rec.target_completion_date - today).days
            else:
                rec.days_to_target = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.course.assignment') or 'New'
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        for rec in self:
            rec.write({
                'state': 'completed',
                'actual_completion_date': rec.actual_completion_date or fields.Date.today(),
            })
            rec.message_post(body=_('Course completed by %s.') % rec.employee_id.name)

    def action_fail(self):
        self.write({'state': 'failed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'assigned', 'actual_completion_date': False, 'score': 0.0})


class VmfHrEmployeeLearning(models.Model):
    """Learning summary on the employee record."""
    _inherit = 'hr.employee'

    course_assignment_ids = fields.One2many('vmf.course.assignment', 'employee_id',
        string='Course Assignments')
    course_assigned_count = fields.Integer('Courses Assigned',
        compute='_compute_course_counts')
    course_completed_count = fields.Integer('Courses Completed',
        compute='_compute_course_counts')
    course_in_progress_count = fields.Integer('Courses In Progress',
        compute='_compute_course_counts')

    @api.depends('course_assignment_ids.state')
    def _compute_course_counts(self):
        for rec in self:
            assignments = rec.course_assignment_ids
            rec.course_assigned_count = len(assignments)
            rec.course_completed_count = len(assignments.filtered(lambda a: a.state == 'completed'))
            rec.course_in_progress_count = len(assignments.filtered(
                lambda a: a.state in ('assigned', 'in_progress')))

    def action_view_course_assignments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Assignments'),
            'res_model': 'vmf.course.assignment',
            'view_mode': 'list,form,kanban',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
