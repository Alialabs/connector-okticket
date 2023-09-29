# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Alia Okticket Connector User Synchronization',
    'summary': 'Implements Okticket user synchronization operations.',
    'version': '10.0.1.0.1',
    'category': 'Connector',
    'depends': [
        'hr',
        'connector_okticket',
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/okticket_hr_employee_view.xml',
        'views/okticket_backend_view.xml',
    ],
    'application': False,
    'installable': True,
}
