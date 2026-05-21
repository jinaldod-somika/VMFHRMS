from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date


class TestVmfPerformance(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        
        # Create HOD 2 Employee
        self.hod2_emp = self.env['hr.employee'].create({
            'name': 'HOD Two',
            'company_id': self.company.id,
            'work_email': 'hod2@example.com',
        })
        
        # Create Manager (HOD 1) Employee
        self.manager_emp = self.env['hr.employee'].create({
            'name': 'HOD One (Manager)',
            'company_id': self.company.id,
            'work_email': 'hod1@example.com',
        })
        
        # Create standard Employee (with Manager and HOD 2 assigned)
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.company.id,
            'parent_id': self.manager_emp.id,
            'vmf_hod2_id': self.hod2_emp.id,
            'work_email': 'emp@example.com',
        })
        
        # Create a user for the employee to test access / write locks
        self.employee_user = self.env['res.users'].create({
            'name': 'Employee User',
            'login': 'emp_user',
            'email': 'emp@example.com',
            'employee_id': self.employee.id,
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('vmf_hrms.group_vmf_employee').id])],
        })
        
        self.employee.user_id = self.employee_user.id

    def test_goal_workflow_full_success(self):
        """ Test a full standalone Goal plan workflow from Draft to Achieved """
        # 1. Create a Goal in draft
        goal = self.env['vmf.goal'].with_user(self.employee_user).create({
            'name': 'Boost Sales',
            'statement': 'Increase sales revenue in Q3 by 20%',
            'weight': 30.0,
            'bsc_perspective': 'financial',
            'success_measure': 'Sales report shows 20% increase',
            'review_frequency': 'quarterly',
            'employee_id': self.employee.id,
        })
        
        self.assertEqual(goal.state, 'draft')
        self.assertEqual(goal.manager_id, self.manager_emp)
        self.assertEqual(goal.hod2_id, self.hod2_emp)
        
        # Add a Milestone
        milestone = self.env['vmf.goal.milestone'].with_user(self.employee_user).create({
            'goal_id': goal.id,
            'measure': 'Q3 Sales Report',
            'description': 'Deliver the mid-quarter report',
            'completion_date': date.today(),
        })
        
        # 2. Employee submits Goal to HOD 1
        goal.with_user(self.employee_user).action_submit()
        self.assertEqual(goal.state, 'submitted')
        
        # 3. Manager (HOD 1) approves but fails because HOD 1 comments are missing
        with self.assertRaises(ValidationError):
            goal.action_hod1_approve()
            
        # Add HOD 1 comment on milestone
        milestone.hod1_comment = 'Good milestone'
        
        # Manager approves successfully
        goal.action_hod1_approve()
        self.assertEqual(goal.state, 'hod1_approved')
        
        # 4. HOD 2 approves but fails because HOD 2 comments are missing
        with self.assertRaises(ValidationError):
            goal.action_hod2_approve()
            
        # Add HOD 2 comment on milestone
        milestone.hod2_comment = 'Approved milestone'
        
        # HOD 2 approves successfully -> Achieved
        goal.action_hod2_approve()
        self.assertEqual(goal.state, 'achieved')

    def test_goal_write_locks(self):
        """ Verify employee edit block after Goal is submitted, HOD date editing, and total lock down once achieved """
        goal = self.env['vmf.goal'].with_user(self.employee_user).create({
            'name': 'Test Write Lock',
            'statement': 'Statement',
            'weight': 20.0,
            'success_measure': 'Measure',
            'employee_id': self.employee.id,
        })
        
        # Employee can edit in draft
        goal.with_user(self.employee_user).write({'name': 'Updated Draft Name'})
        self.assertEqual(goal.name, 'Updated Draft Name')
        
        # Submit Goal
        goal.with_user(self.employee_user).action_submit()
        
        # Employee tries to edit after submission -> should trigger ValidationError
        with self.assertRaises(ValidationError):
            goal.with_user(self.employee_user).write({'name': 'Post Submission Edit Attempt'})
            
        # Manager / HOD can edit dates after submission
        goal.sudo().write({
            'start_date': date(2026, 6, 1),
            'target_date': date(2026, 12, 31)
        })
        self.assertEqual(goal.start_date, date(2026, 6, 1))
        
        # Set milestones to proceed to Achieved state
        milestone = self.env['vmf.goal.milestone'].create({
            'goal_id': goal.id,
            'measure': 'Key metrics',
            'description': 'Description',
            'completion_date': date.today(),
            'hod1_comment': 'Done 1',
        })
        goal.action_hod1_approve()
        
        milestone.hod2_comment = 'Done 2'
        goal.action_hod2_approve()
        self.assertEqual(goal.state, 'achieved')
        
        # Once achieved, no one (not even sudo) can edit the goal details
        with self.assertRaises(ValidationError):
            goal.sudo().write({'weight': 40.0})

    def test_goal_milestone_not_sure(self):
        """ Verify approval works with 'I am not sure' checked and no milestones """
        goal = self.env['vmf.goal'].create({
            'name': 'Flexible Goal',
            'statement': 'Flexible Statement',
            'weight': 20.0,
            'success_measure': 'Flexible Measure',
            'employee_id': self.employee.id,
            'milestone_not_sure': True,
        })
        
        goal.action_submit()
        self.assertEqual(goal.state, 'submitted')
        
        # HOD 1 approves without validation checks on milestones
        goal.action_hod1_approve()
        self.assertEqual(goal.state, 'hod1_approved')
        
        # HOD 2 approves without validation checks on milestones
        goal.action_hod2_approve()
        self.assertEqual(goal.state, 'achieved')

    def test_goal_rejection_and_resubmission(self):
        """ Verify HOD rejection flow reset to draft, sending email, and employee's ability to resubmit """
        goal = self.env['vmf.goal'].create({
            'name': 'Rejection Goal',
            'statement': 'Statement',
            'weight': 20.0,
            'success_measure': 'Measure',
            'employee_id': self.employee.id,
        })
        
        # Submit Goal
        goal.action_submit()
        self.assertEqual(goal.state, 'submitted')
        
        # HOD 1 rejects the goal
        goal.action_reject()
        self.assertEqual(goal.state, 'draft')
        
        # Employee makes modifications and resubmits
        goal.with_user(self.employee_user).write({'weight': 25.0})
        goal.with_user(self.employee_user).action_submit()
        self.assertEqual(goal.state, 'submitted')

    def test_goal_company_record_rules(self):
        """ Verify Goal record rules restrict regular employees to own goals, and managers/HR to active company """
        other_company = self.env['res.company'].create({'name': 'Test Other Company'})
        other_emp = self.env['hr.employee'].create({
            'name': 'Other Employee',
            'company_id': other_company.id,
        })
        other_goal = self.env['vmf.goal'].create({
            'name': 'Other Goal',
            'statement': 'Other Statement',
            'weight': 20.0,
            'success_measure': 'Other Measure',
            'employee_id': other_emp.id,
        })
        
        # Create a user for the manager
        manager_user = self.env['res.users'].create({
            'name': 'Manager User',
            'login': 'mgr_user',
            'email': 'hod1@example.com',
            'employee_id': self.manager_emp.id,
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('vmf_hrms.group_vmf_manager').id])],
        })
        self.manager_emp.user_id = manager_user.id
        
        # 1. Regular employee cannot see other company's goals
        employee_goals = self.env['vmf.goal'].with_user(self.employee_user).search([('id', '=', other_goal.id)])
        self.assertFalse(employee_goals)
        
        # 2. Manager cannot see other company's goals if company is not in active company_ids
        manager_goals = self.env['vmf.goal'].with_user(manager_user).search([('id', '=', other_goal.id)])
        self.assertFalse(manager_goals)
