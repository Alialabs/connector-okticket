# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Alia Okticket Expense Sheet Grouping',
    'summary': 'Implements different expenses grouping in expenses sheet.',
    'version': '10.0.1.0.1',
    'category': 'Connector',
    'depends': [
        'connector_okticket',
        'okticket_connector_hr_expense_sheet',
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'views/hr_expense_sheet_view.xml',
    ],
    'application': False,
    'installable': True,
}
