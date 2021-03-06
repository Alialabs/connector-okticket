# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Alia Okticket Connector Cost Center',
    'summary': 'Implements Okticket cost center operations.',
    'version': '1.0',
    'category': 'Connector',
    'depends': [
        'connector_okticket',
        'project',
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'security/ir.model.access.csv',
        'wizard/project_cost_center_view.xml',
        'views/project_view.xml',
    ],
    'application': False,
    'installable': True,
}
