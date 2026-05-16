from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
from datetime import date


class VmfSalaryStructure(models.Model):
    _name = 'vmf.salary.structure'
    _description = 'Salary Structure'
    _order = 'name'

    name = fields.Char('Structure Name', required=True)
    code = fields.Char('Code', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                   default=lambda self: self.env.company.currency_id)
    employee_category = fields.Selection([
        ('expat_permanent', 'Expat Permanent'),
        ('expat_contractual', 'Expat Contractual'),
        ('national_permanent', 'National Permanent'),
        ('national_contractual', 'National Contractual'),
        ('all', 'All Categories'),
    ], string='Employee Category', default='all')
    country_id = fields.Many2one('res.country', string='Country')
    grade_id = fields.Many2one('vmf.grade', string='Applicable Grade')
    line_ids = fields.One2many('vmf.salary.rule', 'structure_id', string='Salary Rules')
    active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')


class VmfSalaryRule(models.Model):
    _name = 'vmf.salary.rule'
    _description = 'Salary Rule'
    _order = 'sequence'

    structure_id = fields.Many2one('vmf.salary.structure', string='Structure', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Component Name', required=True)
    code = fields.Char('Code', required=True)
    component_type = fields.Selection([
        ('earning', 'Earning'),
        ('deduction', 'Deduction'),
        ('info', 'Information'),
    ], string='Type', required=True, default='earning')
    computation = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percent_basic', 'Percentage of Basic'),
        ('percent_gross', 'Percentage of Gross'),
        ('formula', 'Python Formula'),
    ], string='Computation', required=True, default='fixed')
    amount = fields.Float('Amount / Percentage')
    formula = fields.Text('Formula (Python)', help="Available: basic, gross, net, employee, contract, inputs")
    is_taxable = fields.Boolean('Taxable')
    appears_on_payslip = fields.Boolean('Appears on Payslip', default=True)
    active = fields.Boolean('Active', default=True)


class VmfEmployeeContract(models.Model):
    _name = 'vmf.employee.contract'
    _description = 'Employee Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'

    name = fields.Char('Contract Reference', required=True, default='New Contract')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', store=True)
    grade_id = fields.Many2one('vmf.grade', related='employee_id.vmf_grade_id', store=True)

    date_start = fields.Date('Start Date', required=True, tracking=True)
    date_end = fields.Date('End Date', tracking=True)
    probation_end_date = fields.Date('Probation End Date')
    notice_period_days = fields.Integer('Notice Period (days)', default=30)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)

    structure_id = fields.Many2one('vmf.salary.structure', string='Salary Structure', required=True)
    currency_id = fields.Many2one('res.currency', related='structure_id.currency_id', store=True)
    basic_salary = fields.Monetary('Basic Salary', currency_field='currency_id', tracking=True)

    # Components (for display only — actual amounts computed by rules)
    hra = fields.Monetary('HRA', currency_field='currency_id')
    accommodation_allowance = fields.Monetary('Accommodation Allowance', currency_field='currency_id')
    transport_allowance = fields.Monetary('Transport Allowance', currency_field='currency_id')
    annual_leave_allowance = fields.Monetary('Annual Leave Allowance', currency_field='currency_id')
    other_allowance = fields.Monetary('Other Allowance', currency_field='currency_id')
    gross_salary = fields.Monetary('Gross Salary', currency_field='currency_id',
                                   compute='_compute_gross', store=True)

    # History of revisions
    revision_ids = fields.One2many('vmf.contract.revision', 'contract_id', string='Revision History')

    notes = fields.Text('Notes')

    @api.depends('basic_salary', 'hra', 'accommodation_allowance', 'transport_allowance',
                 'annual_leave_allowance', 'other_allowance')
    def _compute_gross(self):
        for rec in self:
            rec.gross_salary = (rec.basic_salary + rec.hra + rec.accommodation_allowance +
                                rec.transport_allowance + rec.annual_leave_allowance + rec.other_allowance)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_terminate(self):
        self.write({'state': 'terminated'})


class VmfContractRevision(models.Model):
    _name = 'vmf.contract.revision'
    _description = 'Contract / Salary Revision History'
    _order = 'effective_date desc'

    contract_id = fields.Many2one('vmf.employee.contract', string='Contract', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', store=True)
    effective_date = fields.Date('Effective Date', required=True)
    revision_type = fields.Selection([
        ('increment', 'Annual Increment'),
        ('promotion', 'Promotion'),
        ('revision', 'Salary Revision'),
        ('correction', 'Correction'),
    ], string='Revision Type', required=True)
    old_basic = fields.Monetary('Old Basic', currency_field='currency_id')
    new_basic = fields.Monetary('New Basic', currency_field='currency_id')
    old_gross = fields.Monetary('Old Gross', currency_field='currency_id')
    new_gross = fields.Monetary('New Gross', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='contract_id.currency_id', store=True)
    increment_percent = fields.Float('Increment %', compute='_compute_increment', store=True)
    reason = fields.Text('Reason')
    approved_by = fields.Many2one('res.users', string='Approved By')

    @api.depends('old_basic', 'new_basic')
    def _compute_increment(self):
        for rec in self:
            if rec.old_basic:
                rec.increment_percent = ((rec.new_basic - rec.old_basic) / rec.old_basic) * 100
            else:
                rec.increment_percent = 0


class VmfPayrollRun(models.Model):
    _name = 'vmf.payroll.run'
    _description = 'Payroll Run (Monthly Batch)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'

    name = fields.Char('Payroll Run Reference', readonly=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company, tracking=True)
    date_start = fields.Date('Period Start', required=True)
    date_end = fields.Date('Period End', required=True)
    payroll_month = fields.Char('Month / Year', compute='_compute_month', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed / Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    slip_ids = fields.One2many('vmf.payslip', 'payroll_run_id', string='Payslips')
    total_employees = fields.Integer('Total Employees', compute='_compute_totals', store=True)
    total_gross = fields.Monetary('Total Gross', compute='_compute_totals', store=True,
                                  currency_field='currency_id')
    total_deductions = fields.Monetary('Total Deductions', compute='_compute_totals', store=True,
                                       currency_field='currency_id')
    total_net = fields.Monetary('Total Net', compute='_compute_totals', store=True,
                                currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime('Approved Date', readonly=True)
    notes = fields.Text('Run Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vmf.payroll.run') or 'New'
        return super().create(vals_list)

    @api.depends('date_start')
    def _compute_month(self):
        for rec in self:
            rec.payroll_month = rec.date_start.strftime('%B %Y') if rec.date_start else ''

    @api.depends('slip_ids', 'slip_ids.gross_pay', 'slip_ids.total_deductions', 'slip_ids.net_pay')
    def _compute_totals(self):
        for rec in self:
            rec.total_employees = len(rec.slip_ids)
            rec.total_gross = sum(s.gross_pay for s in rec.slip_ids)
            rec.total_deductions = sum(s.total_deductions for s in rec.slip_ids)
            rec.total_net = sum(s.net_pay for s in rec.slip_ids)

    def action_compute_payroll(self):
        """Generate/recompute payslips for all active employees"""
        self.ensure_one()
        if self.state not in ('draft', 'computed'):
            raise exceptions.UserError(_('Can only compute payroll in draft or computed state.'))

        # Find active employees with contracts for this company
        contracts = self.env['vmf.employee.contract'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'active'),
            ('date_start', '<=', self.date_end),
            '|', ('date_end', '=', False), ('date_end', '>=', self.date_start),
        ])

        # Delete existing draft slips
        self.slip_ids.filtered(lambda s: s.state == 'draft').unlink()

        for contract in contracts:
            existing = self.slip_ids.filtered(lambda s: s.employee_id == contract.employee_id)
            if not existing:
                slip = self.env['vmf.payslip'].create({
                    'payroll_run_id': self.id,
                    'employee_id': contract.employee_id.id,
                    'contract_id': contract.id,
                    'date_start': self.date_start,
                    'date_end': self.date_end,
                })
                slip.action_compute()

        self.write({'state': 'computed'})
        self.message_post(body=_('Payroll computed for %d employees.') % len(contracts))

    def action_review(self):
        self.write({'state': 'reviewed'})

    def action_approve(self):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Payroll approved by %s.') % self.env.user.name)

    def action_confirm(self):
        self.ensure_one()
        self.slip_ids.write({'state': 'paid'})
        self.write({'state': 'confirmed'})
        self.message_post(body=_('Payroll confirmed. Payslips marked as paid.'))

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class VmfPayslip(models.Model):
    _name = 'vmf.payslip'
    _description = 'Payslip'
    _inherit = ['mail.thread']
    _order = 'date_start desc'
    _rec_name = 'name'

    name = fields.Char('Payslip Reference', compute='_compute_name', store=True)
    payroll_run_id = fields.Many2one('vmf.payroll.run', string='Payroll Run', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('vmf.employee.contract', string='Contract', required=True)
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    grade_id = fields.Many2one('vmf.grade', related='employee_id.vmf_grade_id', store=True)

    date_start = fields.Date('Period Start', required=True)
    date_end = fields.Date('Period End', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')

    # Working days
    working_days = fields.Float('Working Days')
    paid_days = fields.Float('Paid Days')
    lop_days = fields.Float('LOP Days')

    # Computed pay
    basic_pay = fields.Monetary('Basic Pay', currency_field='currency_id')
    gross_pay = fields.Monetary('Gross Pay', currency_field='currency_id')
    total_deductions = fields.Monetary('Total Deductions', currency_field='currency_id')
    net_pay = fields.Monetary('Net Pay', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='contract_id.currency_id', store=True)

    line_ids = fields.One2many('vmf.payslip.line', 'payslip_id', string='Payslip Lines')
    notes = fields.Text('Notes')

    @api.depends('employee_id', 'date_start')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.date_start:
                rec.name = f"SLIP/{rec.employee_id.vmf_employee_number or rec.employee_id.name}/{rec.date_start.strftime('%m%Y')}"
            else:
                rec.name = 'Draft Payslip'

    def action_compute(self):
        """Compute payslip based on contract rules"""
        self.ensure_one()
        # Clear existing lines
        self.line_ids.unlink()

        contract = self.contract_id
        structure = contract.structure_id
        if not structure:
            return

        # Calculate LOP from leaves
        lop_days = self._get_lop_days()
        self.lop_days = lop_days

        # Calculate working days
        working_days = self._get_working_days()
        self.working_days = working_days
        self.paid_days = max(0, working_days - lop_days)

        proration = self.paid_days / working_days if working_days else 1

        lines_to_create = []
        gross = 0
        deductions = 0
        basic = contract.basic_salary * proration

        for rule in structure.line_ids.filtered(lambda r: r.active).sorted('sequence'):
            amount = self._compute_rule_amount(rule, basic, gross, contract, proration)
            if rule.component_type == 'earning':
                gross += amount
            elif rule.component_type == 'deduction':
                deductions += amount
            if rule.appears_on_payslip:
                lines_to_create.append({
                    'payslip_id': self.id,
                    'rule_id': rule.id,
                    'name': rule.name,
                    'code': rule.code,
                    'component_type': rule.component_type,
                    'amount': amount,
                })

        if lines_to_create:
            self.env['vmf.payslip.line'].create(lines_to_create)

        self.basic_pay = basic
        self.gross_pay = gross
        self.total_deductions = deductions
        self.net_pay = gross - deductions
        self.state = 'computed'

    def _get_lop_days(self):
        """Get LOP days from approved leaves"""
        lop_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', fields.Datetime.to_datetime(self.date_start)),
            ('date_to', '<=', fields.Datetime.to_datetime(self.date_end)),
            ('state', '=', 'validate'),
            ('holiday_status_id.unpaid', '=', True),
        ])
        return sum(leave.number_of_days for leave in lop_leaves)

    def _get_working_days(self):
        """Count working days in period"""
        from datetime import timedelta
        start = self.date_start
        end = self.date_end
        days = 0
        current = start
        while current <= end:
            if current.weekday() < 5:  # Mon-Fri
                days += 1
            current += timedelta(days=1)
        return days

    def _compute_rule_amount(self, rule, basic, gross, contract, proration):
        amount = 0.0
        if rule.computation == 'fixed':
            amount = rule.amount * proration
        elif rule.computation == 'percent_basic':
            amount = basic * (rule.amount / 100)
        elif rule.computation == 'percent_gross':
            amount = gross * (rule.amount / 100)
        elif rule.computation == 'formula':
            try:
                local_dict = {
                    'basic': basic, 'gross': gross, 'net': gross,
                    'employee': contract.employee_id,
                    'contract': contract,
                    'proration': proration,
                    'result': 0,
                }
                exec(rule.formula or 'result = 0', local_dict)
                amount = local_dict.get('result', 0)
            except Exception:
                amount = 0.0
        return max(0, amount)

    def action_print_payslip(self):
        return self.env.ref('vmf_hrms.action_report_payslip').report_action(self)


class VmfPayslipLine(models.Model):
    _name = 'vmf.payslip.line'
    _description = 'Payslip Line'
    _order = 'rule_id'

    payslip_id = fields.Many2one('vmf.payslip', string='Payslip', required=True, ondelete='cascade')
    rule_id = fields.Many2one('vmf.salary.rule', string='Rule')
    name = fields.Char('Component', required=True)
    code = fields.Char('Code')
    component_type = fields.Selection([
        ('earning', 'Earning'),
        ('deduction', 'Deduction'),
        ('info', 'Information'),
    ], string='Type', required=True)
    amount = fields.Monetary('Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='payslip_id.currency_id', store=True)
