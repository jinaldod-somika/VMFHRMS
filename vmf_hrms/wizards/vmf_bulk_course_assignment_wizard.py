from odoo import models, fields, api, _
from odoo.exceptions import UserError

class VmfBulkCourseAssignmentWizard(models.TransientModel):
    _name = 'vmf.bulk.course.assignment.wizard'
    _description = 'Bulk Course Assignment Wizard'

    learning_path_id = fields.Many2one('vmf.learning.path', string='Learning Path', 
        required=True, domain="[('active', '=', True)]")
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
    target_completion_date = fields.Date('Target Completion Date')

    def action_assign(self):
        self.ensure_one()
        if not self.learning_path_id.course_line_ids:
            raise UserError(_("The selected Learning Path has no courses."))
        
        Assignment = self.env['vmf.course.assignment']
        for employee in self.employee_ids:
            for line in self.learning_path_id.course_line_ids:
                # Check if already assigned
                existing = Assignment.search([
                    ('employee_id', '=', employee.id),
                    ('course_id', '=', line.course_id.id),
                    ('state', 'in', ['assigned', 'in_progress'])
                ], limit=1)
                
                if not existing:
                    Assignment.create({
                        'employee_id': employee.id,
                        'course_id': line.course_id.id,
                        'learning_path_id': self.learning_path_id.id,
                        'target_completion_date': self.target_completion_date,
                    })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Learning Path assigned to %s employees.') % len(self.employee_ids),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
