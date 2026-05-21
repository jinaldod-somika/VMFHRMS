from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import re


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _rec_names_search = ['name', 'vmf_employee_number']

    # Clean and robust override of field access for Auditor and general fields
    @api.model
    def _has_field_access(self, field, operation):
        # 1. Allow HR Auditor full read access to all standard HR-protected fields
        if operation == 'read':
            auditor_group = self.env.ref('vmf_hrms.group_vmf_auditor', raise_if_not_found=False)
            if auditor_group and auditor_group in self.env.user.sudo().group_ids:
                hr_groups = {
                    'hr.group_hr_user',
                    'hr.group_hr_manager',
                    'hr_holidays.group_hr_holidays_user',
                    'hr_payroll.group_hr_payroll_user',
                    'hr_recruitment.group_hr_recruitment_user',
                    'vmf_hrms.group_vmf_hr_manager',
                    'vmf_hrms.group_vmf_payroll'
                }
                if field.groups and any(g in field.groups for g in hr_groups):
                    return True


        # 2. Allow general users read access to standard employee fields to prevent view/form crashes
        if operation == 'read':
            # Whitelist custom/specific fields and any field restricted to standard HR Officers
            if field.name in ('exceptional_location_id', 'employee_properties', 'version_id', 'current_version_id') or \
               (field.groups and 'hr.group_hr_user' in field.groups):
                return True

        # 3. Allow standard employees read access to their own sensitive fields
        if operation == 'read' and self and len(self) == 1 and self.id == self.env.user.employee_id.id:
            return True



        return super()._has_field_access(field, operation)

    # Employee number sequence
    vmf_employee_number = fields.Char('Employee Number', copy=False, readonly=True)

    # Computed field to control visibility of sensitive details (statutory, travel, address)
    vmf_show_sensitive_data = fields.Boolean(compute='_compute_vmf_show_sensitive_data', string='Show Sensitive Data')

    def _compute_vmf_show_sensitive_data(self):
        is_privileged = self.env.user.has_group('vmf_hrms.group_vmf_hr_manager') or \
                        self.env.user.has_group('vmf_hrms.group_vmf_payroll') or \
                        self.env.user.has_group('vmf_hrms.group_vmf_auditor') or \
                        self.env.user._is_admin()
        for rec in self:
            rec.vmf_show_sensitive_data = is_privileged or (rec.user_id and rec.user_id == self.env.user)

    # Employee category
    vmf_employee_category = fields.Selection([
        ('expat_permanent', 'Expat Permanent'),
        ('expat_contractual', 'Expat Contractual'),
        ('national_permanent', 'National Permanent'),
        ('national_contractual', 'National Contractual'),
        ('security_agency', 'Security / Agency'),
        ('subcontractor', 'Subcontractor'),
    ], string='Employee Category', tracking=True)

    # Grade
    vmf_grade_id = fields.Many2one('vmf.grade', string='Grade', tracking=True)
    vmf_grade_level = fields.Selection(related='vmf_grade_id.grade_level', store=True, string='Grade Level')

    # Organization
    vmf_business_unit_id = fields.Many2one('vmf.business.unit', string='Business Unit')
    vmf_cost_center_id = fields.Many2one('vmf.cost.center', string='Cost Center')
    vmf_region_id = fields.Many2one('vmf.region', string='Region')
    vmf_hod2_id = fields.Many2one('hr.employee', string='HOD 2')
    vmf_business_hr_id = fields.Many2one('hr.employee', string='Business HR')

    # Address
    vmf_permanent_address = fields.Text('Permanent Address')
    vmf_current_address = fields.Text('Current Address',
        help='Current residential address. Can differ from the permanent address.')

    # Passport & travel docs
    vmf_passport_number = fields.Char('Passport Number', groups='vmf_hrms.group_vmf_hr_manager')
    vmf_passport_expiry = fields.Date('Passport Expiry', groups='vmf_hrms.group_vmf_hr_manager')
    vmf_visa_type = fields.Selection([
        ('pec', 'PEC'),
        ('vvl', 'VVL'),
        ('work_permit', 'Work Permit'),
        ('business', 'Business Visa'),
        ('none', 'None Required'),
    ], string='Current Visa Type')
    vmf_visa_expiry = fields.Date('Visa Expiry')

    # Air ticket entitlement
    vmf_air_ticket_eligibility = fields.Selection([
        ('once_year', 'Once a Year'),
        ('twice_year', 'Twice a Year'),
        ('on_rotation', '30-Day Rotation'),
        ('no_entitlement', 'No Entitlement'),
    ], string='Air Ticket Eligibility')

    # Travel
    vmf_nearest_airport = fields.Many2one('vmf.airport', string='Nearest Airport (Home)')
    vmf_french_eligible = fields.Boolean('French Language Allowance Eligible')

    # India statutory — visible to HR Manager and above (Payroll inherits HR Manager)
    vmf_pan_number = fields.Char('PAN Number', groups='vmf_hrms.group_vmf_hr_manager,vmf_hrms.group_vmf_auditor')
    vmf_aadhar_number = fields.Char('Aadhar Number', groups='vmf_hrms.group_vmf_hr_manager,vmf_hrms.group_vmf_auditor')
    vmf_uan_number = fields.Char('UAN (PF) Number', groups='vmf_hrms.group_vmf_hr_manager,vmf_hrms.group_vmf_auditor')
    vmf_pf_account = fields.Char('PF Account Number', groups='vmf_hrms.group_vmf_hr_manager,vmf_hrms.group_vmf_auditor')
    vmf_esi_number = fields.Char('ESI Number', groups='vmf_hrms.group_vmf_hr_manager,vmf_hrms.group_vmf_auditor')

    @api.constrains('vmf_pan_number')
    def _check_pan_number(self):
        for rec in self:
            if rec.vmf_pan_number:
                if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', rec.vmf_pan_number):
                    raise ValidationError(_("Invalid PAN Number format. It must be 10 characters (e.g., ABCDE1234F)."))

    @api.constrains('vmf_aadhar_number')
    def _check_aadhar_number(self):
        for rec in self:
            if rec.vmf_aadhar_number:
                if not re.match(r'^\d{12}$', rec.vmf_aadhar_number):
                    raise ValidationError(_("Invalid Aadhaar Number. It must be exactly 12 digits."))

    @api.constrains('vmf_uan_number')
    def _check_uan_number(self):
        for rec in self:
            if rec.vmf_uan_number:
                if not re.match(r'^\d{12}$', rec.vmf_uan_number):
                    raise ValidationError(_("Invalid UAN Number. It must be exactly 12 digits."))

    # Employment dates
    vmf_probation_end_date = fields.Date('Probation End Date')
    vmf_confirmation_date = fields.Date('Confirmation Date')
    vmf_contract_end_date = fields.Date('Contract End Date')

    # Onboarding
    vmf_onboarding_completed = fields.Boolean('Onboarding Completed')
    vmf_onboarding_completion_date = fields.Date('Onboarding Completed Date')

    # Separation
    vmf_exit_reason = fields.Selection([
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('contract_end', 'Contract End'),
        ('retirement', 'Retirement'),
        ('death', 'Death'),
        ('absconding', 'Absconding'),
        ('mutual_separation', 'Mutual Separation'),
    ], string='Exit Reason')

    # Rotation type (for expats)
    vmf_rotation_type = fields.Selection([
        ('30_day', '30-Day Rotation'),
        ('once_year', 'Once a Year Leave Travel'),
        ('twice_year', 'Twice a Year Leave Travel'),
        ('no_rotation', 'No Rotation'),
    ], string='Rotation Type')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - {rec.vmf_employee_number}" if rec.vmf_employee_number else rec.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('vmf_employee_number'):
                category = vals.get('vmf_employee_category') or ''
                if 'expat' in category:
                    seq_code = 'vmf.employee.expat'
                elif 'subcontractor' in category:
                    seq_code = 'vmf.employee.subcontractor'
                else:
                    seq_code = 'vmf.employee.national'
                vals['vmf_employee_number'] = self.env['ir.sequence'].next_by_code(seq_code) or ''
        return super().create(vals_list)

    def action_view_travel_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Travel Requests',
            'res_model': 'vmf.travel.request',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_payslips(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payslips',
            'res_model': 'vmf.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
        }

    def action_view_performance_reviews(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Performance Reviews',
            'res_model': 'vmf.performance.review',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
        }


class HrDepartment(models.Model):
    _inherit = 'hr.department'
    _rec_names_search = ['name', 'vmf_department_code']

    vmf_department_code = fields.Char('Department Code')
    vmf_cost_center_id = fields.Many2one('vmf.cost.center', string='Default Cost Center')
    vmf_business_unit_id = fields.Many2one('vmf.business.unit', string='Business Unit')
    vmf_notes = fields.Text('Notes')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - {rec.vmf_department_code}" if rec.vmf_department_code else rec.name

    @api.constrains('vmf_department_code', 'company_id')
    def _check_vmf_department_code_unique(self):
        for rec in self:
            if not rec.vmf_department_code:
                continue
            dupes = self.with_context(active_test=False).search([
                ('vmf_department_code', '=', rec.vmf_department_code),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
            ], limit=1)
            if dupes:
                raise ValidationError(
                    f"Department code '{rec.vmf_department_code}' is already used in this company."
                )


class VmfAirport(models.Model):
    _name = 'vmf.airport'
    _description = 'Airport Master'
    _order = 'code'
    _rec_names_search = ['name', 'code']

    code = fields.Char('IATA Code', required=True, size=3)
    name = fields.Char('Airport Name', required=True)
    city = fields.Char('City')
    country_id = fields.Many2one('res.country', string='Country')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Airport IATA code must be unique!'),
    ]

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - {rec.code}" if rec.code else rec.name
