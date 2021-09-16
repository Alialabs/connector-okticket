# -*- coding: utf-8 -*-
#
#    Created on 2/05/19
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


from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateBatchImporter(Component):
    _name = 'okticket.product.template.batch.importer'
    _inherit = 'okticket.import.mapper'
    _apply_on = 'okticket.product.template'
    _usage = 'importer'

    _ticket_type_id = '0'

    @mapping
    def external_id(self, record):
        external_id = str(record['id'])
        return {'external_id': external_id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def odoo_id(self, record):
        """ Will bind the category on a existing one with the same name."""
        existing = self.env['product.template'].search(
            [('name', '=', record['name']),
             ('can_be_expensed', '=', True),
             ('reinvoiceable_product_version', '=', False)], # El binding del producto se realiza contra la versión "No refacturable"
            # limit=1,
        )
        if existing:
            valid_prod = False
            if len(existing) > 1:
                for prod in existing:
                    if prod.okticket_bind_ids:
                        valid_prod = prod
                        break
            if not valid_prod:
                valid_prod = existing[0]
            return {'odoo_id': valid_prod.id}

    def run(self, filters=None, options=None):
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        # Read users from OkTicket
        okticket_product_template_ids = []
        # Mapper
        mapper = self.component(usage='importer')
        # Binder
        binder = self.component(usage='binder')

        # >>> ATENCIÓN!: sólo se están recuperando los productos (gastos) de tipo "ticket" (type_id= 0) <<<
        for product_ext_vals in backend_adapter.search(filters):
            # Map to odoo data
            internal_data = mapper.map_record(product_ext_vals).values()
            # find if the OkTicket id already exists in odoo
            binding = binder.to_internal(product_ext_vals.get('id'))

            product_to_bind_vals = {
                'type': 'service',
                'can_be_expensed': True,
                'okticket_type_prod_id': int(self._ticket_type_id),
                'okticket_categ_prod_id': product_ext_vals['id'],
            }
            odoo_product = False # Siempre adquiere un valor a lo largo de los if-else...
            if binding: # EXISTE producto y están VINCULADO = ACTUALIZAR
                binding.write(internal_data)
                odoo_product = self.env['product.template'].browse(internal_data['odoo_id'])
                odoo_product.write(product_to_bind_vals)
            else: # NO está VINCULADO
                if not internal_data.get('odoo_id'): # NO EXISTE
                    # Creación del product.product con la información de OkTicket
                    product_to_bind_vals.update({
                        'name': product_ext_vals.get('name'),
                    })
                    odoo_product = self.env['product.template'].create(product_to_bind_vals)
                else: # EXISTE el producto en Odoo pero NO está VINCULADO
                    odoo_product = self.env['product.template'].browse(internal_data['odoo_id'])
                    odoo_product.write(product_to_bind_vals)
                # Vinculación entre el producto creado o ya existente en Odoo y la categoría de gasto de Okticket
                internal_data['odoo_id'] = odoo_product.id
                binding = self.model.create(internal_data)
            if binding:
                okticket_product_template_ids.append(binding.id)
                if 'id' in product_ext_vals:
                    external_id = str(product_ext_vals['id'])
                    binder.bind(external_id, binding)
                    _logger.info('Imported')

            # CREACIÓN/ACTUALIZACIÓN de versión NO-REINVOICEABLE del producto que se está importando
            if odoo_product:
                odoo_product.load_reinvoiceable_product_version()

        _logger.info('Import from Okticket DONE !!!')
        return okticket_product_template_ids


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: