# -*- coding: utf-8 -*-
#
#    Created on 19/07/19
#
#    @author:alia
#
#
# 2019 ALIA Technologies
#       http://www.alialabs.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#


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
        odoo_ids = self.env['okticket.product.template'].search([
            ('external_id', operator, value)]).mapped('odoo_id').ids
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
            result = self.okticket_api.find_products(https=self.collection.https)
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return []
