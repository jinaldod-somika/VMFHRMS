from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrWorkLocation(models.Model):
    _inherit = 'hr.work.location'

    vmf_location_code = fields.Char('Location Code', copy=False)
    vmf_region_id = fields.Many2one('vmf.region', string='Region')
    vmf_notes = fields.Text('Notes')

    @api.constrains('vmf_location_code', 'company_id')
    def _check_vmf_location_code_unique(self):
        for rec in self:
            if not rec.vmf_location_code:
                continue
            dupes = self.with_context(active_test=False).search([
                ('vmf_location_code', '=', rec.vmf_location_code),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
            ], limit=1)
            if dupes:
                raise ValidationError(
                    f"Location code '{rec.vmf_location_code}' is already used in this company."
                )
