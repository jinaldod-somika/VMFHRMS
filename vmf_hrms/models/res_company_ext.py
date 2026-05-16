from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    vmf_company_code = fields.Char('Company Code', copy=False)
    vmf_short_name = fields.Char('Short Name')
    vmf_company_type = fields.Selection([
        ('operating', 'Operating Company'),
        ('holding', 'Holding Company'),
        ('joint_venture', 'Joint Venture'),
        ('subsidiary', 'Subsidiary'),
        ('branch', 'Branch'),
        ('foundation', 'Foundation / Trust'),
        ('shared_services', 'Shared Services'),
    ], string='Company Type')
    vmf_notes = fields.Text('Internal Notes')

    @api.constrains('vmf_company_code')
    def _check_vmf_company_code_unique(self):
        for rec in self:
            if not rec.vmf_company_code:
                continue
            dupes = self.with_context(active_test=False).search([
                ('vmf_company_code', '=', rec.vmf_company_code),
                ('id', '!=', rec.id),
            ], limit=1)
            if dupes:
                raise ValidationError(
                    f"Company code '{rec.vmf_company_code}' is already used by '{dupes.name}'."
                )
