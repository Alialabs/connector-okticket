# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
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
        return {'external_id': str(record['id'])}

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
        if not existing:
            return
        # Prefer a product already bound to *this* backend. The previous version
        # accepted a product bound to any backend, so with several backends the
        # second one adopted -- and rebound to itself -- the product templates
        # of the first company, cross-wiring the bindings.
        own = existing.filtered(
            lambda p: p.okticket_bind_ids.filtered(
                lambda b: b.backend_id == self.backend_record
            )
        )
        if own:
            return {'odoo_id': own[0].id}
        # Then an unbound one, rather than stealing another backend's binding.
        unbound = existing.filtered(lambda p: not p.okticket_bind_ids)
        if unbound:
            return {'odoo_id': unbound[0].id}
        return {'odoo_id': existing[0].id}

    @mapping
    def type(self, record):
        prod_type = 'service'
        return {
            'type': prod_type,
            # 'detailed_type': prod_type
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
        mapper = self.component(usage='importer')
        binder = self.component(usage='binder')
        okticket_product_template_ids = []

        # WARNING: it only gets products (expenses) with type_id = 0 ("ticket" type)
        for product_ext_vals in backend_adapter.search(filters):

            # Map to odoo data
            internal_data = mapper.map_record(product_ext_vals).values()
            # find if the OkTicket product id already exists in odoo
            binding = binder.to_internal(product_ext_vals.get('id'))

            if not binding:
                # Already imported by another backend: reuse it, do not import it
                # again. These products carry no company and every company sees
                # them, and okticket_categ_prod_id resolves through *any*
                # backend's binding, so a second binding for the same OkTicket
                # category would only duplicate. The company-dependent invoice and
                # rebillable links still have to be written for this company,
                # which is what the two load_* calls below do.
                already = self.model.with_context(active_test=False).search(
                    [('external_id', '=', str(product_ext_vals['id'])),
                     ('backend_id', '!=', self.backend_record.id)], limit=1)
                if already:
                    _logger.info('Category %s already imported by backend %s; reusing '
                                 'product %s', product_ext_vals['id'],
                                 already.backend_id.name, already.odoo_id.display_name)
                    odoo_product = binder.unwrap_binding(already)
                    if odoo_product:
                        odoo_product.load_rebillable_product_version()
                        odoo_product.load_invoice_product_version()
                    okticket_product_template_ids.append(already.id)
                    continue
                if internal_data.get('odoo_id'):
                    binding = self.model.search([
                        (binder._odoo_field, '=', internal_data['odoo_id']),
                        (binder._backend_field, '=', self.backend_record.id)
                    ])
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
