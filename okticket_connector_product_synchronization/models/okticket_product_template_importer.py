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

    @mapping
    def type(self, record):
        prod_type = 'service'
        return {
            'type': prod_type,
            'detailed_type': prod_type
        }

    @mapping
    def can_be_expensed(self, record):
        return {'can_be_expensed': True}

    @mapping
    def okticket_type_prod_id(self, record):
        return {'okticket_type_prod_id': int(self._ticket_type_id)}

    @mapping
    def okticket_categ_prod_id(self, record):
        return {'okticket_categ_prod_id': record['id']}

    @mapping
    def name(self, record):
        return {'name': record['name']}

    def run(self, filters=None, options=None):
        backend_adapter = self.component(usage='backend.adapter')
        okticket_product_template_ids = []
        mapper = self.component(usage='importer')
        binder = self.component(usage='binder')

        # WARNING: it only gets products (expenses) with type_id = 0 ("ticket" type)
        for product_ext_vals in backend_adapter.search(filters):

            # Map to odoo data
            internal_data = mapper.map_record(product_ext_vals).values()
            # find if the OkTicket product id already exists in odoo
            binding = binder.to_internal(product_ext_vals.get('id'))

            if not binding:
                if internal_data.get('odoo_id'):
                    binding = self.model.search([(binder._odoo_field, '=', internal_data['odoo_id']),
                                                 (binder._backend_field, '=', self.backend_record.id)])
                if not binding:
                    # Product or product binding do not exist in Odoo
                    binding = self.model.create(internal_data)

            binding.write(internal_data)
            binder.bind(str(product_ext_vals['id']), binding)

            okticket_product_template_ids.append(binding.id)
            _logger.info('Imported')

            odoo_product = binder.unwrap_binding(binding)
            # Creation/update of no refund product version which is being imported
            if odoo_product:
                odoo_product.load_rebillable_product_version()

            # Creation/update of invoice product version which is being imported
            if odoo_product:
                invoice_product_version_ids = odoo_product.load_invoice_product_version()

                # FYI: implementar si se necesitase crear la versión "refacturable"
                #  (reinvoiceable) de la versión "factura" (invoice) de un producto
                # self.env['product.template'].browse(invoice_product_version_ids).load_reinvoiceable_product_version()

        _logger.info(_('Import from Okticket DONE'))
        return okticket_product_template_ids
