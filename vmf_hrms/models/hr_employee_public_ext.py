from odoo import models, fields

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # Safe / Public fields (no group restriction, read-only related)
    vmf_employee_number = fields.Char(related='employee_id.vmf_employee_number', readonly=True)
    vmf_employee_category = fields.Selection(related='employee_id.vmf_employee_category', readonly=True)
    vmf_grade_id = fields.Many2one('vmf.grade', related='employee_id.vmf_grade_id', readonly=True)
    vmf_grade_level = fields.Selection(related='employee_id.vmf_grade_level', readonly=True)
    vmf_business_unit_id = fields.Many2one('vmf.business.unit', related='employee_id.vmf_business_unit_id', readonly=True)
    vmf_region_id = fields.Many2one('vmf.region', related='employee_id.vmf_region_id', readonly=True)
    vmf_hod2_id = fields.Many2one('hr.employee', related='employee_id.vmf_hod2_id', readonly=True)
    vmf_business_hr_id = fields.Many2one('hr.employee', related='employee_id.vmf_business_hr_id', readonly=True)

    # Sensitive related fields
    # Standard Odoo related field security will automatically restrict these fields based on the user's
    # access rights to the private 'hr.employee' target model (preventing data leaks), but without
    # throwing hard field-level Access Errors when general users browse public colleague lists.
    struct_id = fields.Many2one('hr.payroll.structure', related='employee_id.struct_id', readonly=True)
    vmf_cost_center_id = fields.Many2one('vmf.cost.center', related='employee_id.vmf_cost_center_id', readonly=True)
    
    vmf_permanent_address = fields.Text(related='employee_id.vmf_permanent_address', readonly=True)
    vmf_current_address = fields.Text(related='employee_id.vmf_current_address', readonly=True)
    
    vmf_visa_type = fields.Selection(related='employee_id.vmf_visa_type', readonly=True)
    vmf_visa_expiry = fields.Date(related='employee_id.vmf_visa_expiry', readonly=True)
    
    vmf_air_ticket_eligibility = fields.Selection(related='employee_id.vmf_air_ticket_eligibility', readonly=True)
    vmf_nearest_airport = fields.Many2one('vmf.airport', related='employee_id.vmf_nearest_airport', readonly=True)
    vmf_french_eligible = fields.Boolean(related='employee_id.vmf_french_eligible', readonly=True)
    
    vmf_probation_end_date = fields.Date(related='employee_id.vmf_probation_end_date', readonly=True)
    vmf_confirmation_date = fields.Date(related='employee_id.vmf_confirmation_date', readonly=True)
    vmf_contract_end_date = fields.Date(related='employee_id.vmf_contract_end_date', readonly=True)
    
    vmf_onboarding_completed = fields.Boolean(related='employee_id.vmf_onboarding_completed', readonly=True)
    vmf_onboarding_completion_date = fields.Date(related='employee_id.vmf_onboarding_completion_date', readonly=True)
    
    vmf_exit_reason = fields.Selection(related='employee_id.vmf_exit_reason', readonly=True)
    vmf_rotation_type = fields.Selection(related='employee_id.vmf_rotation_type', readonly=True)
    is_hipo = fields.Boolean(related='employee_id.is_hipo', readonly=True)
