{
    'name': "Infinity",

    'summary': "Infinity Project Management",

    'description': """

    """,

    'author': "GBS Team",
    'website': "",
    'application': 'True',

    'category': 'Uncategorized',
    'version': '0.10',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'hr', 'product', 'sale', 'sale_project', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/project_task_views.xml',
        'views/contract_type_views.xml',
        'views/technical_report.xml',
        'views/service_contract_views.xml',
        'views/sale_order_view.xml',
        'views/hr_employee_views.xml',
        'views/machine_data_views.xml',
        'views/spare_parts_views.xml',
        'views/technical_report_pdf.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
