# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    'name': 'Okticket Connector',
    'summary': 'Mainly features, models and business logic for Okticket connector. '
               'Implements expenses import from Okticket.',
    'version': '1.0',
    'category': 'Connector',
    'depends': [
        'hr_expense',
        'sale_expense',
        'queue_job',
        'component',
        'component_event',
        'connector',
        'uom',
        'analytic_base_department',
        'product',
        'hr',
        'project',
        'hr_timesheet'
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'security/okticket_connector_security.xml',
        'security/ir.model.access.csv',

        'data/ir_cron_data.xml',
        'data/product_data.xml',

        'views/okticket_backend_view.xml',
        'views/okticket_menu.xml',
        'views/res_users.xml',
        'views/hr_expense_view.xml',
        'views/product_template_view.xml',
        'views/hr_employee_view.xml',
        'views/company_view.xml',
        'views/project_view.xml',

        'wizard/expense_wizard_view.xml'
    ],
    'application': False,
    'installable': True,
}
