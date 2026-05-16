from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class VmfPerformanceFeedbackWizard(models.TransientModel):
    _name = 'vmf.performance.feedback.wizard'
    _description = 'Performance Feedback Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    feedback_type = fields.Selection([
        ('positive', 'Positive (Appreciation)'),
        ('improvement', 'Constructive (Improvement Area)'),
        ('neutral', 'General Feedback'),
    ], string='Feedback Type', required=True, default='neutral')
    subject = fields.Char('Subject', required=True)
    message = fields.Text('Feedback Message', required=True)
    anonymous = fields.Boolean('Submit Anonymously', help='Only for group feedback or special cases.')

    def action_submit_feedback(self):
        self.ensure_one()
        body = Markup(_('<b>Performance Feedback Received</b><br/>'
                        '<b>Type:</b> %s<br/>'
                        '<b>Subject:</b> %s<br/>'
                        '<b>Message:</b> %s')) % (
            dict(self._fields['feedback_type'].selection).get(self.feedback_type),
            self.subject,
            self.message
        )
        self.employee_id.message_post(body=body)
        
        # Also notify the employee
        if self.employee_id.user_id:
            self.employee_id.message_post(
                body=body,
                partner_ids=self.employee_id.user_id.partner_id.ids,
                message_type='notification'
            )
        return {'type': 'ir.actions.act_window_close'}

class VmfSelfAppraisalWizard(models.TransientModel):
    _name = 'vmf.self.appraisal.wizard'
    _description = 'Self Appraisal Wizard'

    review_id = fields.Many2one('vmf.performance.review', string='Review', required=True, readonly=True)
    achievements = fields.Text('Key Achievements during the period', required=True)
    challenges = fields.Text('Challenges Faced', required=True)
    self_rating = fields.Float('Self Rating (1-5)', required=True)
    learning_needs = fields.Text('Learning & Development Needs')

    def action_submit_self_appraisal(self):
        self.ensure_one()
        self.review_id.write({
            'self_appraisal_comments': f"Achievements: {self.achievements}\nChallenges: {self.challenges}\nLearning Needs: {self.learning_needs}",
            'self_rating': self.self_rating,
            'state': 'manager_review'
        })
        self.review_id.message_post(body=_('Self Appraisal submitted with rating: %s') % self.self_rating)
        return {'type': 'ir.actions.act_window_close'}

class VmfPipInitiateWizard(models.TransientModel):
    _name = 'vmf.pip.initiate.wizard'
    _description = 'PIP Initiation Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    improvement_areas = fields.Text('Areas Requiring Improvement', required=True)
    expected_outcomes = fields.Text('Expected Outcomes / Success Criteria', required=True)
    duration_weeks = fields.Integer('Duration (weeks)', default=12, required=True)
    start_date = fields.Date('Start Date', default=fields.Date.today, required=True)

    def action_confirm_pip(self):
        self.ensure_one()
        end_date = fields.Date.add(self.start_date, weeks=self.duration_weeks)
        pip = self.env['vmf.pip'].create({
            'employee_id': self.employee_id.id,
            'improvement_areas': self.improvement_areas,
            'expected_outcomes': self.expected_outcomes,
            'duration_weeks': self.duration_weeks,
            'date_initiated': self.start_date,
            'date_end': end_date,
            'state': 'active'
        })
        self.employee_id.message_post(body=_('Performance Improvement Plan (PIP) initiated. Reference: %s') % pip.name)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vmf.pip',
            'res_id': pip.id,
            'view_mode': 'form',
        }
