# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Alia Okticket Expense Sheet',
    'summary': 'Implements Okticket expenses sheet operations.',
    'version': '1.0',
    'category': 'Connector',
    'depends': [
        'sale_timesheet',
        'hr_expense',
        'connector_okticket',
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'views/project_view.xml',
        'views/hr_expense_sheet_view.xml',
        'security/ir.model.access.csv',
    ],
    'application': False,
    'installable': True,
}
