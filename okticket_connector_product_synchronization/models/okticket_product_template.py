# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import _, fields, models
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.product.template',
        inverse_name='odoo_id',
        string='Product Product Bindings',
    )

    def _get_categ_prod_id(self):
        for product in self:
            base_product = product.get_base_product()
            external_ids = [okticket_categ_prod.external_id for okticket_categ_prod in base_product.okticket_bind_ids]
            product.okticket_categ_prod_id = external_ids and int(float(external_ids[0])) or -1.0

    def _set_categ_prod_id(self):
        for product in self:
            base_product = product.get_base_product()
            if base_product.okticket_bind_ids:
                base_product.okticket_bind_ids.write({'external_id': product.okticket_categ_prod_id})

    def _search_categ_prod_id(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, int):
            raise ValueError(_('Value should be integer (not %s)'), value)
        domain = []
        odoo_ids = []
        for product in self.env['okticket.product.template'].search([('external_id', operator, value)]).mapped(
                'odoo_id'):
            odoo_ids.append(product.id)
            if product.rebillable_prod_id:
                odoo_ids.append(product.rebillable_prod_id.id)
            if product.invoice_prod_id:
                odoo_ids.append(product.invoice_prod_id.id)

        if odoo_ids:
            domain.append(('id', 'in', odoo_ids))
        return domain

    okticket_categ_prod_id = fields.Integer(default=-1.0,
                                            compute=_get_categ_prod_id,
                                            inverse=_set_categ_prod_id,
                                            search=_search_categ_prod_id)


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


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    okticket_product_template_ids = fields.One2many(
        comodel_name='okticket.product.template',
        inverse_name='backend_id',
        string='Product Template Bindings',
        context={'active_test': False})


class ProductTemplateAdapter(Component):
    _name = 'okticket.product.template.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.product.template'

    def search(self, filters):
        if self._auth():
            # Parámetros por defecto
            params_dict = {'paginate': 'false'}

            result = self.okticket_api.find_products(params=params_dict, https=self.collection.https)
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return []
