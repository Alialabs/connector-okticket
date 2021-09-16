# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

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
             ('rebillable_product_version', '=', False)]
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

        # WARNING: it only gets products (expenses) with type_id = 0 ("ticket" type)
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
            odoo_product = False
            if binding:
                # Exists the product and is bound (UPDATE)
                binding.write(internal_data)
                odoo_product = self.env['product.template'].browse(internal_data['odoo_id'])
                odoo_product.write(product_to_bind_vals)
            else:
                # Product not bound
                if not internal_data.get('odoo_id'):
                    # Product doesn't exist
                    # It creates new product.product based on Okticket data
                    product_to_bind_vals.update({
                        'name': product_ext_vals.get('name'),
                    })
                    odoo_product = self.env['product.template'].create(product_to_bind_vals)
                else:
                    # Product exists in Odoo but doesn't is bound
                    odoo_product = self.env['product.template'].browse(internal_data['odoo_id'])
                    odoo_product.write(product_to_bind_vals)
                # Binding between Odoo product and Okticket expense category
                internal_data['odoo_id'] = odoo_product.id
                binding = self.model.create(internal_data)
            if binding:
                okticket_product_template_ids.append(binding.id)
                if 'id' in product_ext_vals:
                    external_id = str(product_ext_vals['id'])
                    binder.bind(external_id, binding)
                    _logger.info('Imported')
            # Creation/update of no refund product version which is being imported
            if odoo_product:
                odoo_product.load_rebillable_product_version()

        _logger.info(_('Import from Okticket DONE'))
        return okticket_product_template_ids
