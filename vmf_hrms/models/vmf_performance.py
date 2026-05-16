from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import date


class VmfGoalPlan(models.Model):
    _name = 'vmf.goal.plan'
    _description = 'Annual Goal Plan'
    _inherit = ['mail.thread']
    _order = 'year desc'

    name = fields.Char('Goal Plan Name', required=True)
    year = fields.Integer('Year', required=True, default=lambda self: date.today().year)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
    ], default='draft', string='Status', tracking=True)
    goal_ids = fields.One2many('vmf.goal', 'plan_id', string='Goals')
    description = fields.Text('Description')

    def action_publish(self):
        self.write({'state': 'published'})
        self.message_post(body=_('Goal plan published. Employees may now acknowledge their goals.'))


class VmfGoal(models.Model):
    _name = 'vmf.goal'
    _description = 'Performance Goal / KPI'
    _order = 'sequence'

    plan_id = fields.Many2one('vmf.goal.plan', string='Goal Plan', ondelete='cascade')
    name = fields.Char('Goal / KPI Description', required=True)
    sequence = fields.Integer('Sequence', default=10)
    weight = fields.Float('Weightage (%)', default=20)
    target_value = fields.Float('Target Value')
    target_unit = fields.Char('Unit of Measure')
    applicable_to = fields.Selection([
        ('all', 'All Employees'),
        ('grade', 'By Grade'),
        ('department', 'By Department'),
        ('function', 'By Function'),
    ], string='Applicable To', default='all')
    grade_id = fields.Many2one('vmf.grade', string='Grade')
    department_id = fields.Many2one('hr.department', string='Department')
    category = fields.Selection([
        ('financial', 'Financial'),
        ('operational', 'Operational'),
        ('customer', 'Customer'),
        ('people', 'People & Development'),
        ('safety', 'Safety & Compliance'),
    ], string='Category')


class VmfPerformanceReview(models.Model):
    _name = 'vmf.performance.review'
    _description = 'Performance Review / Appraisal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_review desc'
    _rec_name = 'name'

    name = fields.Char('Review Reference', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', store=True, string='Manager')
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    grade_id = fields.Many2one('vmf.grade', related='employee_id.vmf_grade_id', store=True)

    review_type = fields.Selection([
        ('annual', 'Annual Appraisal'),
        ('half_year', 'Half-Yearly Review'),
        ('quarterly', 'Quarterly Check-in'),
        ('monthly', 'Monthly Check-in'),
        ('probation', 'Probation Review'),
        ('pip', 'PIP Review'),
    ], string='Review Type', required=True, default='annual', tracking=True)

    review_period_year = fields.Integer('Year', default=lambda self: date.today().year)
    review_period_quarter = fields.Selection([
        ('q1', 'Q1 (Jan-Mar)'),
        ('q2', 'Q2 (Apr-Jun)'),
        ('q3', 'Q3 (Jul-Sep)'),
        ('q4', 'Q4 (Oct-Dec)'),
    ], string='Quarter')
    date_review = fields.Date('Review Date', default=fields.Date.today)
    date_due = fields.Date('Due Date')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('self_appraisal', 'Self Appraisal'),
        ('manager_review', 'Manager Review'),
        ('calibration', 'Calibration'),
        ('rating_released', 'Rating Released'),
        ('acknowledged', 'Acknowledged'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    goal_line_ids = fields.One2many('vmf.review.goal.line', 'review_id', string='KPI Ratings')

    # Overall ratings
    self_rating = fields.Float('Self Rating (out of 5)')
    manager_rating = fields.Float('Manager Rating (out of 5)', tracking=True)
    final_rating = fields.Float('Final / Calibrated Rating (out of 5)', tracking=True)
    rating_band = fields.Selection([
        ('exceptional', 'Exceptional (4.5-5.0)'),
        ('exceeds_expectations', 'Exceeds Expectations (3.5-4.4)'),
        ('meets_expectations', 'Meets Expectations (2.5-3.4)'),
        ('partially_meets', 'Partially Meets (1.5-2.4)'),
        ('does_not_meet', 'Does Not Meet (Below 1.5)'),
    ], string='Rating Band', compute='_compute_rating_band', store=True)

    # Comments
    self_appraisal_comments = fields.Text('Self Appraisal Comments')
    manager_comments = fields.Text('Manager Comments')
    calibration_comments = fields.Text('Calibration Comments')

    # Development
    strengths = fields.Text('Key Strengths')
    areas_for_improvement = fields.Text('Areas for Improvement')
    development_actions = fields.Text('Development Actions')

    # PIP
    pip_initiated = fields.Boolean('PIP Initiated')
    pip_id = fields.Many2one('vmf.pip', string='PIP Record')

    # Outcome
    increment_recommended = fields.Boolean('Increment Recommended')
    promotion_recommended = fields.Boolean('Promotion Recommended')

    @api.depends('employee_id', 'review_type', 'review_period_year')
    def _compute_name(self):
        for rec in self:
            emp = rec.employee_id.name if rec.employee_id else 'Unknown'
            rec.name = f"REVIEW/{emp}/{rec.review_period_year}/{rec.review_type or 'review'}"

    @api.depends('final_rating', 'manager_rating')
    def _compute_rating_band(self):
        for rec in self:
            r = rec.final_rating or rec.manager_rating or 0
            if r >= 4.5:
                rec.rating_band = 'exceptional'
            elif r >= 3.5:
                rec.rating_band = 'exceeds_expectations'
            elif r >= 2.5:
                rec.rating_band = 'meets_expectations'
            elif r >= 1.5:
                rec.rating_band = 'partially_meets'
            else:
                rec.rating_band = 'does_not_meet'

    def action_start_self_appraisal(self):
        self.write({'state': 'self_appraisal'})

    def action_submit_self(self):
        self.write({'state': 'manager_review'})

    def action_submit_manager(self):
        self.write({'state': 'calibration'})

    def action_release_rating(self):
        self.write({'state': 'rating_released'})
        self.message_post(body=_('Rating released. Employee notified.'))

    def action_acknowledge(self):
        self.write({'state': 'acknowledged'})


class VmfReviewGoalLine(models.Model):
    _name = 'vmf.review.goal.line'
    _description = 'Review KPI / Goal Line'
    _order = 'sequence'

    review_id = fields.Many2one('vmf.performance.review', string='Review', required=True, ondelete='cascade')
    goal_id = fields.Many2one('vmf.goal', string='Goal / KPI')
    name = fields.Char('KPI Description', required=True)
    sequence = fields.Integer('Sequence', default=10)
    weight = fields.Float('Weightage (%)')
    target = fields.Float('Target')
    unit = fields.Char('Unit')
    actual_achievement = fields.Float('Actual Achievement')
    self_rating = fields.Float('Self Rating (1-5)')
    manager_rating = fields.Float('Manager Rating (1-5)')
    final_rating = fields.Float('Final Rating (1-5)')
    self_comments = fields.Text('Self Comments')
    manager_comments = fields.Text('Manager Comments')
    weighted_score = fields.Float('Weighted Score', compute='_compute_weighted', store=True)

    @api.depends('weight', 'final_rating', 'manager_rating')
    def _compute_weighted(self):
        for rec in self:
            r = rec.final_rating or rec.manager_rating or 0
            rec.weighted_score = (rec.weight / 100) * r


class VmfPIP(models.Model):
    _name = 'vmf.pip'
    _description = 'Performance Improvement Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char('PIP Reference', readonly=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', store=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)

    date_initiated = fields.Date('PIP Start Date', default=fields.Date.today)
    date_end = fields.Date('PIP End Date')
    duration_weeks = fields.Integer('Duration (weeks)', default=12)

    state = fields.Selection([
        ('active', 'Active'),
        ('extended', 'Extended'),
        ('closed_improved', 'Closed — Improved'),
        ('closed_exited', 'Closed — Exited'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active', tracking=True)

    improvement_areas = fields.Text('Areas Requiring Improvement', required=True)
    expected_outcomes = fields.Text('Expected Outcomes / Success Criteria', required=True)
    support_provided = fields.Text('Support / Resources Provided')
    review_checkpoint_ids = fields.One2many('vmf.pip.checkpoint', 'pip_id', string='Review Checkpoints')
    closure_reason = fields.Text('Closure Reason')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.pip') or 'New'
        return super().create(vals_list)

    def action_close_improved(self):
        self.write({'state': 'closed_improved'})

    def action_close_exited(self):
        self.write({'state': 'closed_exited'})


class VmfPIPCheckpoint(models.Model):
    _name = 'vmf.pip.checkpoint'
    _description = 'PIP Review Checkpoint'
    _order = 'checkpoint_date'

    pip_id = fields.Many2one('vmf.pip', string='PIP', required=True, ondelete='cascade')
    checkpoint_date = fields.Date('Checkpoint Date', required=True)
    reviewer_id = fields.Many2one('hr.employee', string='Reviewer')
    progress_notes = fields.Text('Progress Notes')
    rating = fields.Selection([
        ('on_track', 'On Track'),
        ('partial', 'Partial Progress'),
        ('no_progress', 'No Progress'),
        ('regressed', 'Regressed'),
    ], string='Progress Status')
    outcome = fields.Selection([
        ('continue', 'Continue PIP'),
        ('extend', 'Extend PIP'),
        ('close_improved', 'Close — Improved'),
        ('exit', 'Exit Process'),
    ], string='Outcome')
