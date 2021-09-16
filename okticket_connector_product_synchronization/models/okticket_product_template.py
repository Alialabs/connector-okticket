# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import fields, models
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.product.template',
        inverse_name='odoo_id',
        string='Product Product Bindings',
    )
    okticket_categ_prod_id = fields.Integer(readonly=True)


class OkticketProductTemplate(models.Model):
    _name = 'okticket.product.template'
    _inherit = 'okticket.binding'
    _inherits = {'product.template': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='cascade',
    )


class ProductTemplateAdapter(Component):
    _name = 'okticket.product.template.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.product.template'

    def search(self, filters):
        if self._auth():
            result = self.okticket_api.find_products(https=self.collection.https)
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return []
