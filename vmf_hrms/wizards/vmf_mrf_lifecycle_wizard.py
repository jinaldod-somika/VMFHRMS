from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup


class VmfMrfHoldWizard(models.TransientModel):
    """Wizard to put an MRF On Hold with a mandatory reason."""
    _name = 'vmf.mrf.hold.wizard'
    _description = 'Put MRF On Hold'

    mrf_id = fields.Many2one('vmf.mrf', string='MRF', required=True, readonly=True)
    hold_reason = fields.Text(
        string='Hold Reason',
        required=True,
        help='Provide the reason for putting this requisition on hold.'
    )
    expected_resume_date = fields.Date(
        string='Expected Resume Date',
        help='Estimated date when recruitment will resume.'
    )
    notify_hiring_manager = fields.Boolean(
        string='Notify Hiring Manager',
        default=True,
        help='Send an email notification to the hiring manager.'
    )

    def action_confirm_hold(self):
        self.ensure_one()
        mrf = self.mrf_id
        if mrf.state not in ('budget_approved', 'in_progress'):
            raise UserError(_(
                'Only MRFs in "Budget Approved" or "In Progress" state can be put on hold.'
            ))

        # Create a hold log entry
        self.env['vmf.mrf.hold'].create({
            'mrf_id': mrf.id,
            'hold_start_date': fields.Date.today(),
            'hold_end_date': self.expected_resume_date or False,
            'hold_reason': self.hold_reason,
            'previous_state': mrf.state,
        })

        # Update MRF state
        mrf.write({
            'previous_state': mrf.state,
            'state': 'on_hold',
            'hold_reason': self.hold_reason,
        })

        # Post chatter message
        msg = Markup(_('<b>MRF placed On Hold</b><br/>'
                       '<b>Reason:</b> %s')) % self.hold_reason
        if self.expected_resume_date:
            msg += Markup(_('<br/><b>Expected Resume:</b> %s')) % self.expected_resume_date
        mrf.message_post(body=msg)

        # Notify hiring manager if requested
        if self.notify_hiring_manager and mrf.hiring_manager_id.user_id:
            mrf.message_post(
                body=msg,
                partner_ids=mrf.hiring_manager_id.user_id.partner_id.ids,
                message_type='email',
                subtype_xmlid='mail.mt_comment',
            )

        return {'type': 'ir.actions.act_window_close'}


class VmfMrfDropWizard(models.TransientModel):
    """Wizard to Cancel/Drop an MRF with a mandatory reason."""
    _name = 'vmf.mrf.drop.wizard'
    _description = 'Cancel / Drop MRF'

    mrf_id = fields.Many2one('vmf.mrf', string='MRF', required=True, readonly=True)
    drop_reason = fields.Selection([
        ('budget_cut', 'Budget Cut / Freeze'),
        ('role_eliminated', 'Role Eliminated'),
        ('internal_filled', 'Filled Internally'),
        ('business_restructure', 'Business Restructuring'),
        ('requirement_changed', 'Requirement Changed'),
        ('other', 'Other'),
    ], string='Drop Reason', required=True)
    drop_notes = fields.Text(
        string='Additional Notes',
        help='Provide any additional context for this cancellation.'
    )
    notify_hiring_manager = fields.Boolean(
        string='Notify Hiring Manager',
        default=True
    )

    def action_confirm_drop(self):
        self.ensure_one()
        mrf = self.mrf_id
        if mrf.state in ('cancelled', 'filled'):
            raise UserError(_('This MRF is already closed and cannot be cancelled again.'))

        # Build reason label
        reason_label = dict(self._fields['drop_reason'].selection).get(self.drop_reason, self.drop_reason)

        # Update MRF state
        mrf.write({'state': 'cancelled'})

        # Post chatter message
        msg = Markup(_('<b>MRF Cancelled / Dropped</b><br/>'
                       '<b>Reason:</b> %s')) % reason_label
        if self.drop_notes:
            msg += Markup(_('<br/><b>Notes:</b> %s')) % self.drop_notes
        mrf.message_post(body=msg)

        # Notify hiring manager if requested
        if self.notify_hiring_manager and mrf.hiring_manager_id.user_id:
            mrf.message_post(
                body=msg,
                partner_ids=mrf.hiring_manager_id.user_id.partner_id.ids,
                message_type='email',
                subtype_xmlid='mail.mt_comment',
            )

        return {'type': 'ir.actions.act_window_close'}


class VmfMrfReopenWizard(models.TransientModel):
    """Wizard to Reopen an On-Hold MRF."""
    _name = 'vmf.mrf.reopen.wizard'
    _description = 'Reopen MRF from Hold'

    mrf_id = fields.Many2one('vmf.mrf', string='MRF', required=True, readonly=True)
    reopen_notes = fields.Text(
        string='Reopen Notes',
        required=True,
        help='Provide reason/context for resuming this requisition.'
    )

    def action_confirm_reopen(self):
        self.ensure_one()
        mrf = self.mrf_id
        if mrf.state != 'on_hold':
            raise UserError(_('Only On Hold MRFs can be reopened.'))

        # Close any open hold log entry
        open_holds = mrf.hold_line_ids.filtered(lambda h: not h.hold_end_date)
        open_holds.write({
            'hold_end_date': fields.Date.today(),
            'resumed_by': self.env.user.id,
            'reopen_reason': self.reopen_notes,
        })

        # Restore state from previous_state
        state_to_restore = mrf.previous_state or 'budget_approved'
        mrf.write({
            'state': state_to_restore,
            'hold_reason': False,
        })

        msg = Markup(_('<b>MRF Reopened / Resumed</b><br/>'
                       '<b>Notes:</b> %s')) % self.reopen_notes
        mrf.message_post(body=msg)

        return {'type': 'ir.actions.act_window_close'}
