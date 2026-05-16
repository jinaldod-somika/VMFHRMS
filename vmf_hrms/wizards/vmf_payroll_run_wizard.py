from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import date
import calendar


class VmfPayrollRunWizard(models.TransientModel):
    _name = 'vmf.payroll.run.wizard'
    _description = 'Create Payroll Run Wizard'

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    year = fields.Integer('Year', required=True, default=lambda self: date.today().year)
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True, default=str(date.today().month))

    def action_create_payroll_run(self):
        month_int = int(self.month)
        _, last_day = calendar.monthrange(self.year, month_int)
        date_start = date(self.year, month_int, 1)
        date_end = date(self.year, month_int, last_day)

        existing = self.env['vmf.payroll.run'].search([
            ('company_id', '=', self.company_id.id),
            ('date_start', '=', date_start),
            ('date_end', '=', date_end),
            ('state', '!=', 'cancelled'),
        ])
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'vmf.payroll.run',
                'res_id': existing[0].id,
                'view_mode': 'form',
            }

        run = self.env['vmf.payroll.run'].create({
            'company_id': self.company_id.id,
            'date_start': date_start,
            'date_end': date_end,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vmf.payroll.run',
            'res_id': run.id,
            'view_mode': 'form',
        }
