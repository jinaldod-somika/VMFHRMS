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


class VmfCandidateInvitationWizard(models.TransientModel):
    _name = 'vmf.candidate.invitation.wizard'
    _description = 'Send Interview Invitation'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    round_number = fields.Selection([
        ('1', 'Round 1'),
        ('2', 'Round 2'),
        ('3', 'Round 3'),
    ], string='Interview Round', required=True, readonly=True)
    interview_date = fields.Date('Interview Date', required=True)
    email = fields.Char('Candidate Email',
                        help='Pre-filled from candidate record. You may update it here if missing or incorrect.')
    interviewer_ids = fields.Many2many('hr.employee', string='Interviewers', required=True)
    hr_interviewer_id = fields.Many2one('hr.employee', string='HR Interviewer', required=True)
    google_meet_link = fields.Char('Google Meet / Invitation Link', help="Enter Google Meet or any other interview link details")

    @api.model
    def default_get(self, fields_list):
        res = super(VmfCandidateInvitationWizard, self).default_get(fields_list)
        candidate_id = res.get('candidate_id') or self._context.get('default_candidate_id')
        round_no = res.get('round_number') or self._context.get('default_round_number')

        if candidate_id:
            candidate = self.env['vmf.candidate'].browse(candidate_id)
            # Pre-fill candidate email
            if candidate.email:
                res['email'] = candidate.email

            if round_no:
                # Default interviewers from previous round if Round 2 or 3
                prev_round = str(int(round_no) - 1)
                if prev_round in ['1', '2']:
                    res.update({
                        'interviewer_ids': [(6, 0, getattr(candidate, f'interview{prev_round}_interviewer_ids').ids)],
                        'hr_interviewer_id': getattr(candidate, f'interview{prev_round}_hr_interviewer_id').id,
                    })
                
                # Prefill Google Meet link for current round if it exists
                current_meet_link = getattr(candidate, f'interview{round_no}_google_meet_link', False)
                if current_meet_link:
                    res['google_meet_link'] = current_meet_link
        return res

    def action_confirm_invitation(self):
        self.ensure_one()
        candidate = self.candidate_id
        round_no = self.round_number

        if not self.email:
            raise UserError(_("Candidate email is required to send an interview invitation. Please enter the email address."))

        # Save email back to candidate if it was added/corrected here
        if self.email != candidate.email:
            candidate.email = self.email

        # Update candidate record
        vals = {
            f'interview{round_no}_date': self.interview_date,
            f'interview{round_no}_interviewer_ids': [(6, 0, self.interviewer_ids.ids)],
            f'interview{round_no}_hr_interviewer_id': self.hr_interviewer_id.id,
            f'interview{round_no}_google_meet_link': self.google_meet_link,
            'state': f'invitation_{round_no}'
        }
        candidate.write(vals)

        # Prepare email template and send
        template = self.env.ref(f'vmf_hrms.email_template_vmf_interview_{round_no}_invitation', raise_if_not_found=False)
        if template:
            # Add CC: Interviewers and HR Interviewer
            cc_emails = []
            for emp in self.interviewer_ids:
                if emp.work_email:
                    cc_emails.append(emp.work_email)
            if self.hr_interviewer_id.work_email:
                cc_emails.append(self.hr_interviewer_id.work_email)
            
            # Post message and send mail
            email_values = {'email_cc': ','.join(cc_emails)} if cc_emails else {}
            template.sudo().send_mail(candidate.id, force_send=True, email_values=email_values)

        candidate.message_post(body=Markup(_('<b>%s Round Invitation Sent</b><br/>'
                                             '<b>Date:</b> %s<br/>'
                                             '<b>HR Interviewer:</b> %s<br/>'
                                             '<b>Interviewers:</b> %s<br/>'
                                             '<b>Google Meet Link:</b> %s')) % (
            round_no, self.interview_date, self.hr_interviewer_id.name, ', '.join(self.interviewer_ids.mapped('name')),
            self.google_meet_link or 'None'))
            
        return {'type': 'ir.actions.act_window_close'}


class VmfCandidateFeedbackWizard(models.TransientModel):
    _name = 'vmf.candidate.feedback.wizard'
    _description = 'Interview Feedback Wizard'

    candidate_id = fields.Many2one('vmf.candidate', string='Candidate', required=True, readonly=True)
    round_number = fields.Selection([
        ('1', 'Round 1'),
        ('2', 'Round 2'),
        ('3', 'Round 3'),
    ], string='Interview Round', required=True, readonly=True)
    result = fields.Selection([
        ('cleared', 'Cleared'),
        ('rejected', 'Rejected'),
        ('result_pending', 'Result Pending'),
        ('no_show', 'No Show'),
    ], string='Result', required=True)
    feedback = fields.Text('Feedback', required=True)
    remarks = fields.Text('Remarks (Optional)')

    def action_confirm_feedback(self):
        self.ensure_one()
        candidate = self.candidate_id
        round_no = self.round_number

        vals = {
            f'interview{round_no}_result': self.result,
            f'interview{round_no}_feedback': self.feedback,
            f'interview{round_no}_remarks': self.remarks,
        }
        candidate.write(vals)

        result_label = dict(self._fields['result'].selection).get(self.result)
        candidate.message_post(body=Markup(_('<b>%s Feedback Submitted</b><br/>'
                                             '<b>Result:</b> %s<br/>'
                                             '<b>Feedback:</b> %s<br/>'
                                             '<b>Remarks:</b> %s')) % (
            round_no, result_label, self.feedback, self.remarks or 'N/A'))
            
        return {'type': 'ir.actions.act_window_close'}
