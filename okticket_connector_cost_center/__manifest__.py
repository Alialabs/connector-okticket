# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Alia Okticket Connector Cost Center',
    'summary': 'Implements Okticket cost center operations.',
    'version': '10.0.1.0.3',
    'category': 'Connector',
    'depends': [
        'connector_okticket',
        'project',
        'sale'
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'security/ir.model.access.csv',
        'wizard/analytic_cost_center_view.xml',
        'views/okticket_analytic_account_view.xml',
        'views/account_analytic_account_view.xml',
        'views/okticket_backend_view.xml',
    ],
    'application': False,
    'installable': True,
}
