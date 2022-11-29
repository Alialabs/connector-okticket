# -*- coding: utf-8 -*-
# Copyright 2015-01/10/22 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    'name': 'Okticket HR Timesheet Cost Center',
    'summary': 'When a new company is created with hr_timesheet addon, a new project is created too. '
               'That starts an Odoo analytic account - Okticket cost center synchronization. '
               'This add-on manages this process.',
    'version': '15.0.1.0.1',
    'category': 'Connector',
    'depends': [
        'hr_timesheet',
        'okticket_connector_cost_center',
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
    ],
    'application': False,
    # 'installable': True,
    'auto_install': ['hr_timesheet', 'okticket_connector_cost_center']
}
