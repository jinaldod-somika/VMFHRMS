from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
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


from odoo.exceptions import ValidationError

class VmfGoal(models.Model):
    _name = 'vmf.goal'
    _description = 'Performance Goal / KPI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    plan_id = fields.Many2one('vmf.goal.plan', string='Goal Plan', ondelete='cascade', required=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, default=lambda self: self.env.user.employee_id)
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', store=True, string='Manager (HOD 1)')
    hod2_id = fields.Many2one('hr.employee', related='employee_id.vmf_hod2_id', store=True, string='HOD 2')
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True, string='Company')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True, string='Department')
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', store=True, string='Job Position')

    name = fields.Char('Goal Name', required=True, tracking=True)
    statement = fields.Text('Goal Statement', required=True, tracking=True)
    weight = fields.Float('Weightage (%)', required=True, default=20.0, tracking=True)

    start_date = fields.Date('Start Date', required=True, default=fields.Date.context_today, tracking=True)
    target_date = fields.Date('Target Date', required=True, default=fields.Date.context_today, tracking=True)

    bsc_perspective = fields.Selection([
        ('financial', 'Financial'),
        ('customer', 'Customer'),
        ('process', 'Internal Process'),
        ('learning', 'Learning & Growth'),
    ], string='BSC Perspective', required=True, default='financial', tracking=True)

    success_measure = fields.Text('Success Measure Details', required=True)
    comments = fields.Text('Add Your Comments')

    review_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half-Yearly'),
        ('annual', 'Annual'),
    ], string='Frequency of Review', required=True, default='annual', tracking=True)

    milestone_not_sure = fields.Boolean('I am not sure as of now')
    milestone_ids = fields.One2many('vmf.goal.milestone', 'goal_id', string='Milestones')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to HOD 1'),
        ('hod1_approved', 'HOD 1 Approved'),
        ('achieved', 'Achieved'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    def write(self, vals):
        is_privileged = self.env.su or \
                        self.env.user.id == 1 or \
                        self.env.user._is_system() or \
                        self.env.user.has_group('vmf_hrms.group_vmf_manager') or \
                        self.env.user.has_group('vmf_hrms.group_vmf_hr_manager') or \
                        self.env.user.has_group('vmf_hrms.group_vmf_group_hr') or \
                        self.env.user.has_group('base.group_system')
        for rec in self:
            # Block any edits (except status transitions) once in Achieved stage
            if rec.state == 'achieved':
                if any(k != 'state' for k in vals.keys()):
                    raise ValidationError(_("You cannot edit a goal that has been achieved."))

            is_privileged_rec = is_privileged or \
                                (rec.manager_id and rec.manager_id.user_id == self.env.user) or \
                                (rec.hod2_id and rec.hod2_id.user_id == self.env.user)
            if rec.state != 'draft' and not is_privileged_rec:
                if any(k != 'state' for k in vals.keys()):
                    raise ValidationError(_("You cannot edit a goal after it has been submitted."))
        return super().write(vals)

    def action_submit(self):
        for rec in self:
            if not rec.manager_id:
                raise ValidationError(_("No Manager (HOD 1) is defined for this employee. Please contact HR."))
            rec.write({'state': 'submitted'})
            rec.message_post(body=_("Goal submitted to HOD 1 (Manager) for approval."))
            
            # Send Email to HOD 1
            template = self.env.ref('vmf_hrms.mail_template_vmf_goal_submitted', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(rec.id, force_send=True)

    def action_hod1_approve(self):
        for rec in self:
            if not rec.manager_id:
                raise ValidationError(_("No Manager (HOD 1) is defined for this employee."))
            
            # Milestone Validation
            if not rec.milestone_not_sure:
                if not rec.milestone_ids:
                    raise ValidationError(_("You must have at least one milestone or select 'I am not sure as of now'."))
                for ms in rec.milestone_ids:
                    if not ms.hod1_comment or not ms.hod1_comment.strip():
                        raise ValidationError(_("Please add HOD 1 comments in milestones before approving."))

            rec.write({'state': 'hod1_approved'})
            rec.message_post(body=_("HOD 1 (Manager) approved the goal plan and submitted to HOD 2."))

            # Send Email to HOD 2
            template = self.env.ref('vmf_hrms.mail_template_vmf_goal_hod1_approved', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(rec.id, force_send=True)

    def action_hod2_approve(self):
        for rec in self:
            if not rec.hod2_id:
                raise ValidationError(_("No HOD 2 is defined for this employee. Please assign an HOD 2."))
            
            # Milestone Validation
            if not rec.milestone_not_sure:
                if not rec.milestone_ids:
                    raise ValidationError(_("You must have at least one milestone or select 'I am not sure as of now'."))
                for ms in rec.milestone_ids:
                    if not ms.hod2_comment or not ms.hod2_comment.strip():
                        raise ValidationError(_("Please add HOD 2 comments in milestones before approving."))

            rec.write({'state': 'achieved'})
            rec.message_post(body=_("HOD 2 approved the goal plan. State is now Achieved."))

            # Send Final Email to Employee
            template = self.env.ref('vmf_hrms.mail_template_vmf_goal_achieved', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(rec.id, force_send=True)

    def action_reject(self):
        for rec in self:
            if rec.state not in ['submitted', 'hod1_approved']:
                raise ValidationError(_("Only submitted or HOD 1 approved goals can be rejected."))
            rec.write({'state': 'draft'})
            rec.message_post(body=_("Goal plan has been rejected and sent back to draft for modification."))

            # Send Email to Employee
            template = self.env.ref('vmf_hrms.mail_template_vmf_goal_rejected', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(rec.id, force_send=True)

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class VmfGoalMilestone(models.Model):
    _name = 'vmf.goal.milestone'
    _description = 'Goal Milestone'
    _order = 'id asc'

    goal_id = fields.Many2one('vmf.goal', string='Goal', required=True, ondelete='cascade')
    measure = fields.Char('Milestone Measures', required=True)
    description = fields.Text('Description', required=True)
    completion_date = fields.Date('Completion Date', required=True)
    hod1_comment = fields.Text('HOD 1 Comment')
    hod2_comment = fields.Text('HOD 2 Comment')



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
        ('acknowledged', 'Acknowledged'),
        ('self_appraisal', 'Self Appraisal'),
        ('manager_review', 'Manager Reviewed'),
        ('calibration', 'HR Calibration'),
        ('released', 'Rating Released'),
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

    def action_acknowledge(self):
        for rec in self:
            total_weight = sum(rec.goal_line_ids.mapped('weight'))
            if total_weight != 100.0:
                raise UserError(_("The total weight of KPIs must be exactly 100%."))
            rec.write({'state': 'acknowledged'})
            rec.message_post(body=_("Goals acknowledged by employee."))

    def action_start_self_appraisal(self):
        self.write({'state': 'self_appraisal'})

    def action_submit_self(self):
        self.write({'state': 'manager_review'})

    def action_submit_manager(self):
        self.write({'state': 'calibration'})

    def action_release_rating(self):
        for rec in self:
            rec.state = 'released'
            final_score = rec.final_rating or rec.manager_rating or 0.0
            if final_score < 2.5:
                # Auto-initiate PIP
                pip = self.env['vmf.pip'].create({
                    'employee_id': rec.employee_id.id,
                    'improvement_areas': 'Rating below 2.5 in recent appraisal.',
                    'expected_outcomes': 'Improve performance to minimum 3.0 level.',
                })
                rec.pip_id = pip.id
                rec.pip_initiated = True
                rec.message_post(body=_("Rating released. Score < 2.5. PIP automatically initiated: %s") % pip.name)
            else:
                rec.message_post(body=_("Rating released. Increment/Promotion letters can now be generated."))


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
