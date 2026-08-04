# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
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

    okticket_categ_prod_id = fields.Integer(
        default=-1.0,
        compute='_compute_okticket_categ_prod_id',
        inverse='_inverse_okticket_categ_prod_id',
        search='_search_okticket_categ_prod_id',
    )

    def _compute_okticket_categ_prod_id(self):
        for product in self:
            base_product = product.get_base_product()
            external_ids = [okticket_categ_prod.external_id for okticket_categ_prod in base_product.okticket_bind_ids]
            product.okticket_categ_prod_id = int(float(external_ids[0])) if external_ids else -1.0

    def _inverse_okticket_categ_prod_id(self):
        for product in self:
            base_product = product.get_base_product()
            if base_product.okticket_bind_ids:
                base_product.okticket_bind_ids.write({'external_id': product.okticket_categ_prod_id})

    def _search_okticket_categ_prod_id(self, operator, value):
        # Odoo 19 normalizes '='/'!=' into 'in'/'not in' before calling field search
        if operator in ('=', '!='):
            operator = 'in' if operator == '=' else 'not in'
            value = [value]
        if operator not in ('in', 'not in'):
            raise ValueError(_('This operator is not supported'))
        base_products = self.env['okticket.product.template'].search(
            [('external_id', 'in', list(value))]).mapped('odoo_id')
        # The category binding only lives on the base product; include its
        # invoice version (okticket_type_prod_id=1) so "Factura" expenses can
        # resolve their -Invoiceable product. Rebillable versions are
        # intentionally excluded: get_base_product first resolves the
        # base/invoice product and then swaps to its rebillable version itself
        # when the expense is refacturable, so adding them here would let a plain
        # ticket (type_id=0) resolve to the "-Rebillable" product instead.
        products = base_products | base_products.mapped('invoice_prod_id')
        return [('id', 'not in' if operator == 'not in' else 'in', products.ids)]


class OkticketProductTemplate(models.Model):
    _name = 'okticket.product.template'
    _description = 'Okticket Product Template Binding'
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
        context={'active_test': False}
    )


class ProductTemplateAdapter(Component):
    _name = 'okticket.product.template.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.product.template'

    def search(self, filters):
        if not self._auth():
            return []

        params_dict = {'paginate': 'false'}
        result = self.okticket_api.find_products(params=params_dict, https=self.collection.https)

        result['log'].update({
            'backend_id': self.backend_record.id,
            'type': result['log'].get('type') or 'success',
        })
        self.env['log.event'].add_event(result['log'])

        if isinstance(result['result'], bool):
            return []

        return result['result']
