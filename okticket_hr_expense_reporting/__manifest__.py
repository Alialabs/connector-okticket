# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Alia Okticket Hr Expense Reporting',
    'summary': 'Implements Okticket Expense reporting.',
    'version': '10.0.1.0.2',
    'category': 'Reporting',
    'depends': [
        'okticket_connector_hr_expense_sheet',
        'web',
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'report/hr_expense_sheet_report.xml',
        'report/hr_expense_report.xml',
        'report/reports.xml',
    ],
    'application': False,
    'installable': True,
}
