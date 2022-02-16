# -*- coding: utf-8 -*-
#
#    Created on 16/04/19
#
#    @author:alia
#
#
# 2019 ALIA Technologies
#       http://www.alialabs.com
#
#
{'name': 'Okticket Connector',
 'version': '12.0.1.0.2',
 'category': 'Connector',
 'depends': [
             # 'project_department',
             'hr_expense',
             'sale_expense',
             'queue_job',
             'component',
             'component_event',
             'connector','uom',
             'analytic_base_department',
             # Modulos necesarios para incluir _id
             'product', 'hr', 'project', 'hr_timesheet'
             ],
 'author': "Alia Technologies",
 'license': 'AGPL-3',
 'website': 'http://www.alialabs.com',
 'data': [
        'data/ir_cron_data.xml',
        'data/product_data.xml',
        # 'data/okticket_connector_user_data.xml',
        # 'data/product_data.xml',
        'security/ir.model.access.csv',
        'views/okticket_backend_view.xml',
        'views/okticket_menu.xml',
        'views/res_users.xml',
        'views/hr_expense_view.xml',
        # Vistas con id de okticket
        'views_mods/product_template_view.xml',
        'views_mods/hr_employee_view.xml',
        'views_mods/company_view.xml',
        'views_mods/project_view.xml',
        'wizard/expense_wizard_view.xml'
    ],
    'application': False,
    'installable': True,
}