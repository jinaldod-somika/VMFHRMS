from odoo import models, fields, api
import re
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    vmf_ifsc_code = fields.Char('IFSC Code', help='11-character alphanumeric Indian Financial System Code')

    @api.constrains('vmf_ifsc_code')
    def _check_ifsc_code(self):
        for record in self:
            if record.vmf_ifsc_code:
                # IFSC format: 4 alphabets, 1 zero, 6 alphanumeric characters
                if not re.match(r'^[A-Za-z]{4}0[A-Za-z0-9]{6}$', record.vmf_ifsc_code):
                    raise ValidationError(_("Invalid IFSC Code format. It should be 11 characters long, where the first 4 are alphabets, 5th is '0', and the last 6 are alphanumeric."))

    @api.constrains('vmf_ifsc_code', 'partner_id', 'bank_id')
    def _check_ifsc_code_required(self):
        for record in self:
            is_india = False
            if record.bank_id and record.bank_id.country and record.bank_id.country.code == 'IN':
                is_india = True
            elif record.partner_id and record.partner_id.country_id and record.partner_id.country_id.code == 'IN':
                is_india = True
                
            if is_india and not record.vmf_ifsc_code:
                raise ValidationError(_("IFSC Code is required for bank accounts in India."))
