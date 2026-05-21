from odoo import models, fields, api


class VmfGrade(models.Model):
    _name = 'vmf.grade'
    _description = 'VMG Grade Master'
    _order = 'sequence, name'

    name = fields.Char('Grade Code', required=True, copy=False)
    description = fields.Char('Grade Description')
    grade_level = fields.Selection([
        ('workmen', 'Workmen (W1-W4)'),
        ('supervisory', 'Supervisory (S1-S5)'),
        ('management', 'Management (M1-M8)'),
        ('senior_management', 'Senior Management (M9-M12)'),
    ], string='Grade Level', required=True)
    sequence = fields.Integer('Sequence', default=10)
    min_salary_usd = fields.Float('Min Salary (USD)')
    max_salary_usd = fields.Float('Max Salary (USD)')
    min_salary_inr = fields.Float('Min Salary (INR)')
    max_salary_inr = fields.Float('Max Salary (INR)')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Grade code must be unique!'),
    ]


class VmfJobGrade(models.Model):
    """Links job positions to grades"""
    _inherit = 'hr.job'

    grade_id = fields.Many2one('vmf.grade', string='Grade')
    grade_level = fields.Selection(related='grade_id.grade_level', store=True, string='Grade Level')
    job_level = fields.Selection([
        ('entry', 'Entry Level'),
        ('junior', 'Junior'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead / Specialist'),
        ('manager', 'Manager'),
        ('senior_manager', 'Senior Manager'),
        ('director', 'Director'),
        ('director_track', 'Director Track'),
        ('vp', 'VP / Head of Function'),
        ('c_level', 'C-Level'),
    ], string='Job Level')
    is_critical_role = fields.Boolean('Critical Role', default=False)
    succession_plan_warning = fields.Char('Succession Plan Status', compute='_compute_succession_warning')

    @api.depends('is_critical_role')
    def _compute_succession_warning(self):
        for rec in self:
            if rec.is_critical_role:
                plan = self.env['vmf.succession.plan'].search([
                    ('critical_role_id', '=', rec.id),
                    ('state', '=', 'active')
                ], limit=1)
                if not plan or plan.successor_count == 0:
                    rec.succession_plan_warning = "⚠️ Critical Role requires an active Succession Plan with successors."
                else:
                    rec.succession_plan_warning = False
            else:
                rec.succession_plan_warning = False
    min_experience_years = fields.Integer('Min Experience (years)')


class VmfCostCenter(models.Model):
    _name = 'vmf.cost.center'
    _description = 'Cost Center'
    _order = 'code'
    _rec_names_search = ['name', 'code']

    code = fields.Char('Cost Center Code', required=True, copy=False)
    name = fields.Char('Cost Center Name', required=True)
    company_id = fields.Many2one('res.company', string='Company')
    active = fields.Boolean('Active', default=True)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - {rec.code}" if rec.code else rec.name

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'Cost center code must be unique per company!'),
    ]


class VmfBusinessUnit(models.Model):
    _name = 'vmf.business.unit'
    _description = 'Business Unit'
    _order = 'name'
    _rec_names_search = ['name', 'code']

    name = fields.Char('Business Unit Name', required=True)
    code = fields.Char('BU Code', copy=False)
    company_id = fields.Many2one('res.company', string='Company')
    active = fields.Boolean('Active', default=True)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - {rec.code}" if rec.code else rec.name


class VmfRegion(models.Model):
    _name = 'vmf.region'
    _description = 'Region / Geography'
    _order = 'name'
    _rec_names_search = ['name', 'code']

    name = fields.Char('Region Name', required=True)
    code = fields.Char('Region Code', copy=False)
    active = fields.Boolean('Active', default=True)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - {rec.code}" if rec.code else rec.name
