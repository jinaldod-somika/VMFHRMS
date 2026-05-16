from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from markupsafe import Markup

class VmfCandidateHoldWizard(models.TransientModel):
    _name = 'vmf.candidate.hold.wizard'
    _description = 'Put Candidate On Hold'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    hold_reason = fields.Text('Hold Reason', required=True)
    expected_resume_date = fields.Date('Expected Resume Date')

    def action_confirm_hold(self):
        self.ensure_one()
        candidate = self.candidate_id
        self.env['vmf.candidate.hold'].create({
            'candidate_id': candidate.id,
            'hold_start': fields.Date.today(),
            'hold_end': self.expected_resume_date,
            'hold_reason': self.hold_reason,
            'previous_state': candidate.state,
        })
        candidate.write({
            'previous_state': candidate.state,
            'state': 'on_hold',
            'hold_reason': self.hold_reason,
        })
        candidate.message_post(body=Markup(_('<b>Candidate placed on hold</b><br/>'
                                             '<b>Reason:</b> %s')) % self.hold_reason)
        return {'type': 'ir.actions.act_window_close'}

class VmfCandidateDropWizard(models.TransientModel):
    _name = 'vmf.candidate.drop.wizard'
    _description = 'Offer Drop Wizard'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    drop_stage = fields.Selection([
        ('after_ol', 'After Offer Letter'),
        ('no_show', 'No Show on Joining'),
        ('during_notice', 'Dropped During Notice Period'),
        ('before_bgv', 'Before BGV Completion'),
        ('visa_rejected', 'Visa Rejected'),
    ], string='Drop Stage', required=True)
    drop_reason = fields.Text('Drop Reason', required=True)
    notes = fields.Text('Additional Notes')

    def action_confirm_drop(self):
        self.ensure_one()
        candidate = self.candidate_id
        self.env['vmf.candidate.drop'].create({
            'candidate_id': candidate.id,
            'drop_date': fields.Date.today(),
            'drop_stage': self.drop_stage,
            'drop_reason': self.drop_reason,
            'notes': self.notes,
            'previous_state': candidate.state,
        })
        candidate.write({
            'previous_state': candidate.state,
            'state': 'offer_dropped',
            'drop_reason': self.drop_reason,
        })
        stage_label = dict(self._fields['drop_stage'].selection).get(self.drop_stage)
        candidate.message_post(body=Markup(_('<b>Offer dropped at stage:</b> %s<br/>'
                                             '<b>Reason:</b> %s')) % (stage_label, self.drop_reason))
        return {'type': 'ir.actions.act_window_close'}

class VmfCandidateMedicalWizard(models.TransientModel):
    _name = 'vmf.candidate.medical.wizard'
    _description = 'Candidate Medical Wizard'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    medical_status = fields.Selection([
        ('fit', 'Fit'),
        ('conditional', 'Conditional Fit'),
        ('unfit', 'Unfit'),
    ], string='Medical Status', required=True)
    medical_clearance_date = fields.Date('Medical Clearance Date', default=fields.Date.today)
    medical_remarks = fields.Text('Medical Remarks')

    def action_confirm_medical(self):
        self.ensure_one()
        self.candidate_id.write({
            'medical_status': self.medical_status,
            'medical_clearance_date': self.medical_clearance_date,
            'notes': (self.candidate_id.notes or '') + '\nMedical Remarks: ' + (self.medical_remarks or ''),
            'state': 'medical' if self.medical_status in ('fit', 'conditional') else self.candidate_id.state
        })
        self.candidate_id.message_post(body=_('Medical status updated to %s on %s') % (dict(self._fields['medical_status'].selection).get(self.medical_status), self.medical_clearance_date))
        return {'type': 'ir.actions.act_window_close'}

class VmfCandidateBgvWizard(models.TransientModel):
    _name = 'vmf.candidate.bgv.wizard'
    _description = 'Candidate BGV Wizard'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    bgv_status = fields.Selection([
        ('initiated', 'Initiated'),
        ('clear', 'Clear'),
        ('discrepancy', 'Discrepancy'),
        ('waived', 'Waived'),
    ], string='BGV Status', required=True)
    bgv_date = fields.Date('Date', default=fields.Date.today)
    bgv_remarks = fields.Text('BGV Remarks')

    def action_confirm_bgv(self):
        self.ensure_one()
        vals = {'bgv_status': self.bgv_status, 'bgv_remarks': self.bgv_remarks}
        if self.bgv_status == 'initiated':
            vals['bgv_initiated_date'] = self.bgv_date
            vals['state'] = 'bgv'
        elif self.bgv_status in ('clear', 'waived'):
            vals['bgv_completed_date'] = self.bgv_date
        
        self.candidate_id.write(vals)
        self.candidate_id.message_post(body=_('BGV status updated to %s') % dict(self._fields['bgv_status'].selection).get(self.bgv_status))
        return {'type': 'ir.actions.act_window_close'}

class VmfCandidateVisaWizard(models.TransientModel):
    _name = 'vmf.candidate.visa.wizard'
    _description = 'Candidate Visa Wizard'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    visa_type = fields.Selection([
        ('pec', 'PEC'),
        ('vvl', 'VVL'),
        ('not_required', 'Travel Not Required'),
        ('business', 'Business Visa'),
        ('work_permit', 'Work Permit'),
    ], string='Visa Type', required=True)
    action_date = fields.Date('Action Date', default=fields.Date.today)
    action_type = fields.Selection([
        ('initiated', 'Initiated'),
        ('received', 'Received'),
    ], string='Action Type', required=True)

    def action_confirm_visa(self):
        self.ensure_one()
        vals = {'visa_type': self.visa_type}
        if self.action_type == 'initiated':
            vals['pec_initiated_date'] = self.action_date
            vals['state'] = 'visa'
        else:
            vals['visa_received_date'] = self.action_date
            
        self.candidate_id.write(vals)
        self.candidate_id.message_post(body=_('Visa/PEC %s on %s') % (self.action_type, self.action_date))
        return {'type': 'ir.actions.act_window_close'}


class VmfCandidateReopenWizard(models.TransientModel):
    _name = 'vmf.candidate.reopen.wizard'
    _description = 'Reopen Candidate'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    reopen_notes = fields.Text('Reopen Notes', required=True)

    def action_confirm_reopen(self):
        self.ensure_one()
        candidate = self.candidate_id
        if candidate.state != 'on_hold':
            raise UserError(_('Only On Hold candidates can be reopened.'))

        # Close hold log
        open_holds = candidate.hold_ids.filtered(lambda h: not h.hold_end)
        open_holds.write({
            'hold_end': fields.Date.today(),
            'reopen_reason': self.reopen_notes,
        })

        state_to_restore = candidate.previous_state or 'new'
        candidate.write({
            'state': state_to_restore,
            'hold_reason': False,
        })
        candidate.message_post(body=Markup(_('<b>Candidate Reopened</b><br/>'
                                             '<b>Notes:</b> %s')) % self.reopen_notes)
        return {'type': 'ir.actions.act_window_close'}
