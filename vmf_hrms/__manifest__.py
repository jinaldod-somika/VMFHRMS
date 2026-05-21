{
    'name': 'VMG HRMS',
    'version': '19.0.1.1.0',
    'category': 'Human Resources',
    'summary': 'End-to-end HRMS for Vinmart Group — MRF, Recruitment, Payroll, Travel, Performance, Exit',
    'description': """
VMG HRMS — Vinmart Group Human Resource Management System
==========================================================
Covers:
- Manpower Requisition (MRF) with multi-level approval
- Extended Candidate Lifecycle (BGV, Medical, Visa, Offer Drop, Hold)
- Employee Master Extensions (grade, category, air ticket eligibility, passport, etc.)
- Custom Payroll Engine (earnings, deductions, LOP, bank advice, payslips)
- Travel Management (multi-agent quotation, visa, ticket booking)
- Performance Management (goal cascading, PIP, 360 feedback, calibration)
- Compensation Planning (increment cycle, budget envelopes)
- Exit Management (no-dues clearance, F&F settlement, relieving letter)
- Headcount Reporting (monthly snapshot with deviation justification)
- Grievance Management with SLA tracking
- Employee Experience (30-60-90 day surveys, digital recognition)
- Group HR Dashboards and Analytics
- Master data extensions on Companies, Work Locations, Departments, Job Positions
- Learning Management (course catalog, learning paths, course assignments, effectiveness tracking)
- Talent Management (competency matrix, skill gap analysis, IDP, 9-box talent review, succession planning)
    """,
    'author': 'VMG IT',
    'website': 'https://www.vinmartgroup.com',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_recruitment',
        'hr_recruitment_skills',
        'hr_skills',
        'hr_holidays',
        'hr_attendance',
        'hr_work_entry',
        'hr_work_entry_holidays',
        'hr_expense',
        'hr_org_chart',
        'hr_maintenance',
        'hr_gamification',
        'survey',
        'mail',
        'base_setup',
        'base',
        'om_hr_payroll',
        'hr_homeworking',
    ],
    'data': [
        # Security
        'security/vmf_security.xml',
        'security/ir.model.access.csv',
        # Sequences & data
        'data/vmf_sequence_data.xml',
        'data/vmf_grade_data.xml',
        'data/vmf_airport_data.xml',
        'data/vmf_admin_user_data.xml',
        'data/vmf_mail_template_data.xml',
        # Wizards (must be before menu)
        'wizards/vmf_payroll_run_wizard_views.xml',
        'wizards/vmf_headcount_report_wizard_views.xml',
        'wizards/vmf_mrf_lifecycle_wizard_views.xml',
        'wizards/vmf_candidate_lifecycle_wizard_views.xml',
        'wizards/vmf_exit_learning_wizard_views.xml',
        'wizards/vmf_performance_ess_wizard_views.xml',
        'wizards/vmf_bulk_course_assignment_wizard_views.xml',
        # Master data view extensions
        'views/res_company_ext_views.xml',
        'views/hr_work_location_ext_views.xml',
        'views/hr_department_ext_views.xml',
        'views/hr_job_ext_views.xml',
        # VMG views
        'views/vmf_grade_views.xml',
        'views/vmf_mrf_views.xml',
        'views/vmf_candidate_views.xml',
        'views/hr_employee_ext_views.xml',
        'views/res_partner_bank_ext_views.xml',
        'views/vmf_payroll_views.xml',
        'views/vmf_travel_views.xml',
        'views/vmf_exit_views.xml',
        'views/vmf_performance_views.xml',
        'views/vmf_grievance_views.xml',
        'views/vmf_headcount_views.xml',
        'views/vmf_learning_views.xml',
        'views/vmf_talent_views.xml',
        'views/vmf_dashboard_views.xml',
        'views/vmf_menu.xml',
        # Reports
        'reports/vmf_payslip_report.xml',
        'reports/vmf_headcount_report.xml',
        'reports/vmf_offer_letter_report.xml',
        'reports/vmf_relieving_letter_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vmf_hrms/static/src/css/vmf_hrms.css',
            'vmf_hrms/static/src/js/vmf_dashboard.js',
            'vmf_hrms/static/src/xml/vmf_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
}
