from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import date
import calendar


class VmfHeadcountReportWizard(models.TransientModel):
    _name = 'vmf.headcount.report.wizard'
    _description = 'Generate Headcount Report Wizard'

    year = fields.Integer('Year', required=True, default=lambda self: date.today().year)
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True, default=str(date.today().month))
    company_ids = fields.Many2many('res.company', string='Companies',
                                   default=lambda self: self.env['res.company'].search([]))
    overwrite_existing = fields.Boolean('Overwrite Existing Snapshot', default=False)

    def action_generate(self):
        month_int = int(self.month)
        snapshot_date = date(self.year, month_int, 1)

        if self.overwrite_existing:
            existing = self.env['vmf.headcount.snapshot'].search([
                ('snapshot_date', '=', snapshot_date),
                ('company_id', 'in', self.company_ids.ids),
            ])
            existing.unlink()

        snapshots = self.env['vmf.headcount.snapshot'].generate_snapshot(
            snapshot_date=snapshot_date,
            company_ids=self.company_ids.ids,
        )

        if not snapshots:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'Headcount Report',
            'res_model': 'vmf.headcount.snapshot',
            'view_mode': 'list,form',
            'domain': [('id', 'in', [s.id for s in snapshots])],
        }
