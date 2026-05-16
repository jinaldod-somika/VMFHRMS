from odoo import models, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'work_entry_source' in self.env['hr.contract']._fields:
                if not vals.get('work_entry_source'):
                    vals['work_entry_source'] = 'calendar'
        return super().create(vals_list)
