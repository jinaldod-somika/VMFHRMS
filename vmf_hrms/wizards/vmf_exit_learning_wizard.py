from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class VmfExitInterviewWizard(models.TransientModel):
    _name = 'vmf.exit.interview.wizard'
    _description = 'Exit Interview Wizard'

    exit_id = fields.Many2one('vmf.exit.request', string='Exit Request', required=True, readonly=True)
    interview_date = fields.Date('Interview Date', default=fields.Date.today, required=True)
    interviewer_id = fields.Many2one('hr.employee', string='Interviewer', required=True)
    exit_reason_category = fields.Selection([
        ('better_opportunity', 'Better Opportunity (Salary/Role)'),
        ('higher_studies', 'Higher Studies'),
        ('personal_reasons', 'Personal / Family Reasons'),
        ('relocation', 'Relocation'),
        ('health_issues', 'Health Issues'),
        ('dissatisfaction', 'Dissatisfaction with Management/Culture'),
        ('retirement', 'Retirement'),
        ('other', 'Other'),
    ], string='Primary Reason for Leaving', required=True)
    detailed_reason = fields.Text('Detailed Feedback', required=True)
    would_rejoin = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe'),
    ], string='Would Rejoin?', required=True)
    recommend_company = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string='Recommend Company to Others?', required=True)

    def action_confirm_interview(self):
        self.ensure_one()
        self.exit_id.write({
            'exit_interview_done': True,
            'exit_interview_date': self.interview_date,
            'exit_reason_detail': self.detailed_reason,
            'would_rejoin': self.would_rejoin,
            'state': 'hr_processing' if self.exit_id.state == 'manager_approved' else self.exit_id.state
        })
        msg = Markup(_('<b>Exit Interview completed</b> on %s by %s.<br/>'
                       '<b>Primary Reason:</b> %s')) % (
            self.interview_date, 
            self.interviewer_id.name, 
            dict(self._fields['exit_reason_category'].selection).get(self.exit_reason_category)
        )
        self.exit_id.message_post(body=msg)
        return {'type': 'ir.actions.act_window_close'}

class VmfCourseFeedbackWizard(models.TransientModel):
    _name = 'vmf.course.feedback.wizard'
    _description = 'Course Feedback Wizard'

    assignment_id = fields.Many2one('vmf.course.assignment', string='Course Assignment', required=True, readonly=True)
    rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string='Overall Rating', required=True)
    feedback_text = fields.Text('Feedback / Comments', required=True)
    relevant_to_job = fields.Boolean('Relevant to my current job?')

    def action_submit_feedback(self):
        self.ensure_one()
        self.assignment_id.write({
            'feedback_employee': self.feedback_text,
            'effectiveness_rating': self.rating,
        })
        self.assignment_id.message_post(body=_('Feedback submitted by employee. Rating: %s') % self.rating)
        return {'type': 'ir.actions.act_window_close'}
