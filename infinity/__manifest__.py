{
    'name': "Infinity",

    'summary': "Infinity Project Management",

    'description': """

    """,

    'author': "GBS Team",
    'website': "",
    'application': True,

    'category': 'Uncategorized',
    'version': '0.62',

    # Stated rather than left to the default: a manifest odoo.sh cannot read
    # is reported as 'not installable', and these two make that reading
    # unambiguous.
    'installable': True,
    # Visits History is hung under Helpdesk from here, where Helpdesk is
    # installed - see hooks.py for why it cannot be done in XML.
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    # mrp is what a Sales Kit is: its Bill of Materials holds the components,
    # and the one ticked Engine there names the machine.
    # timesheet_grid is what the Timesheets 'To Validate' screen comes
    # from, and its list view is the one the SLA Sub Type column is added to.
    'depends': ['base', 'project', 'hr', 'product', 'sale', 'sale_project',
                'sale_stock', 'account', 'mrp', 'timesheet_grid'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/project_task_views.xml',
        'views/contract_type_views.xml',
        'views/technical_report.xml',
        'views/service_contract_views.xml',
        'views/sale_order_view.xml',
        'views/stock_picking_views.xml',
        'views/mrp_bom_views.xml',
        'views/hr_employee_views.xml',
        'views/res_company_views.xml',
        'views/spare_parts_views.xml',
        'views/account_analytic_line_views.xml',
        'views/technical_report_pdf.xml',
    ],
}
