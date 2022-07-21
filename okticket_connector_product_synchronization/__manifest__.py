# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Alia Okticket Connector Product Synchronization',
    'summary': 'Implements Okticket product synchronization operations.',
    'version': '15.0.1.0.4',
    'category': 'Connector',
    'depends': [
        'okticket_connector',
    ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/okticket_product_template_view.xml',
        'views/okticket_backend_view.xml',
    ],
    'application': False,
    'installable': True,
}
