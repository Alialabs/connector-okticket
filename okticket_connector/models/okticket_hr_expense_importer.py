# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import base64
import datetime
import logging

import requests
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

from . import hr_expense

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _name = 'okticket.expenses.batch.importer'
    _inherit = 'okticket.import.mapper'
    _apply_on = 'okticket.hr.expense'
    _usage = 'importer'

    @mapping
    def name(self, record):
        return {'name': record.get('name') or record.get('ticket_num') or record.get('_id')}

    @mapping
    def external_id(self, record):
        return {'external_id': record['_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the category on a existing one with the same name."""
        existing = self.env['hr.expense'].search(
            [('name', '=', record['_id'])],
            limit=1,
        )
        if existing:
            return {'odoo_id': existing.id}

    def get_base_product(self, record):
        """ Gets product of expenses """
        params = []
        existing = False
        if 'type_id' in record:
            # Gasto: type_id = 0; Factura: type_id = 1; Kilómetros: type_id = 2
            params = [('okticket_type_prod_id', '=', record['type_id'])]
            if record['type_id'] in [0, 1]:  # Gastos y facturas
                params.append(('okticket_categ_prod_id', '=', record['category_id']))
            existing = self.env['product.product'].search(params, limit=1)

            # By default, it's used 'no refacturable' in product.template
            # If 'custom_field' from Okticket expense is
            # 'refacturable'="1" ("0": False='no refacturable'; "1": True='refacturable')
            # then it's choosen 'refacturable' in Odoo's product
            if 'custom_fields' in record and 'refacturable' in record['custom_fields'] and \
                    ((isinstance(record['custom_fields']['refacturable'], int) and
                      record['custom_fields']['refacturable'] == 1) or
                     (isinstance(record['custom_fields']['refacturable'], str) and
                      record['custom_fields']['refacturable'] == '1')):
                if existing.rebillable_prod_id:
                    existing = self.env['product.product']. \
                        search([('product_tmpl_id', '=', existing.rebillable_prod_id.id)], limit=1)
        return existing

    @mapping
    def product_id(self, record):
        existing = self.get_base_product(record)
        if existing:
            result = {'product_id': existing.id}
            if record['type_id'] != 0:
                # Assign taxes on product only if it is not of the "ticket" type.
                tax_ids = [(4, stax.id) for stax in existing.supplier_taxes_id]
                if tax_ids:
                    result.update({'tax_ids': tax_ids, })
            return result

    @mapping
    def amount(self, record):
        return {
            'unit_amount': 0.0,  # Para hacer visibles los impuestos en la interfaz Odoo 15
            'total_amount': record['amount']
        }

    @mapping
    def date(self, record):
        if record.get('date'):
            date_time = datetime.datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S')
            return {'date': date_time.date()}

    @mapping
    def comments(self, record):
        return {'description': record['comments']}

    @mapping
    def company_id(self, record):
        if record.get('user_id'):
            backend = self.env['okticket.backend'].search([('okticket_company_id', '=', record['company_id'])],
                                                          limit=1, )
            if backend:
                return {'company_id': backend.company_id.id}

    @mapping
    def employee_id(self, record):
        if record.get('user_id'):
            existing = self.env['hr.employee'].search([('okticket_user_id', '=', record['user_id'])], limit=1, )
            if existing:
                return {'employee_id': existing.id}

    @mapping
    def okticket_status(self, record):
        return {'okticket_status': record['status_id'] == 1 and 'confirmed' or 'pending'}

    @mapping
    def okticket_vat(self, record):
        if 'cif' in record:
            return {'okticket_vat': record['cif']}

    @mapping
    def okticket_partner_name(self, record):
        if 'name' in record and 'type_id' in record and record['type_id'] == 1:
            return {'okticket_partner_name': record['name']}

    @mapping
    def okticket_remote_path(self, record):
        if 'remote_path' in record:
            return {'okticket_remote_path': record['remote_path']}

    @mapping
    def okticket_remote_uri(self, record):
        if 'remote_uri' in record:
            img_path = self.backend_record.image_base_url + record['remote_uri']
            okticket_img = base64.b64encode(requests.get(img_path).content)
            return {
                'okticket_remote_uri': record['remote_uri'],
                'okticket_img': okticket_img
            }

    @mapping
    def payment_method(self, record):
        payment_method = 'na'
        if record.get('payment_method') and \
                record['payment_method'] in [tuple_sel[0] for tuple_sel in hr_expense._payment_method_selection]:
            payment_method = record['payment_method']
        return {'payment_method': payment_method}

    @mapping
    def payment_mode(self, record):
        payment_mode = 'own_account'
        if record.get('custom_fields') and record['custom_fields'].get('refundable') \
                and record['custom_fields']['refundable'] == 'payed':
            payment_mode = 'company_account'
        return {'payment_mode': payment_mode}

    @mapping
    def analytic_account_id(self, record):
        if record.get('cost_center_id'):
            cc_analytic_binder = self.env['okticket.account.analytic.account'].search([
                ('external_id', '=', int(record['cost_center_id']))],
                limit=1, )
            if cc_analytic_binder and cc_analytic_binder.odoo_id:
                fields = {
                    'analytic_account_id': cc_analytic_binder.odoo_id.id
                }
                sale_order = cc_analytic_binder.odoo_id.get_related_sale_order()
                if sale_order:
                    fields.update({'sale_order_id': sale_order.id})
                return fields

    @mapping
    def account_id(self, record):
        """
        The ledger account of the related project is preferably assigned.
        If it does not have any, it is searched from within the product.
        """
        if record.get('cost_center_id'):
            cc_analytic_binder = self.env['okticket.account.analytic.account'].search([
                ('external_id', '=', int(record['cost_center_id']))],
                limit=1)
            if cc_analytic_binder and cc_analytic_binder.odoo_id:
                # Ledger account of the related project
                okticket_account_id = cc_analytic_binder.odoo_id.okticket_def_account_id \
                                              and cc_analytic_binder.odoo_id.okticket_def_account_id.id \
                                              or False
                if not okticket_account_id:
                    # Ledger account from within the product
                    existing = self.get_base_product(record)
                    if existing.property_account_expense_id:
                        okticket_account_id = existing.property_account_expense_id.id
                if okticket_account_id:
                    return {
                        'account_id': okticket_account_id,
                    }

    @mapping
    def reference(self, record):
        return {'reference': record.get('ticket_num') or 'N.A.'}

    @mapping
    def is_invoice(self, record):
        return {'is_invoice': record.get('type_id') and record['type_id'] == 1 or False}

    def run(self, filters=None, options=None):
        """
        Run the synchronization for all users, using the connector crons.
        """
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        # Expenses values from OkTicket
        okticket_hr_expense_ids = []
        # Mapper
        mapper = self.component(usage='importer')
        # Binder
        binder = self.component(usage='binder')

        # Fields needed to be able to import a expense
        required_fields = ['product_id', 'employee_id', 'company_id']

        # All expenses not in "sent" state (this is, state = "draft") are eliminated before new import or
        # synchronization of expenses from OkTicket. This way, we ensure Odoo-OkTicket synchronization.
        states_to_remove = ['draft']
        expenses_to_remove = self.env['hr.expense'].search([('state', 'in', states_to_remove)])
        expenses_to_remove = self.env['hr.expense'].browse([exp.id for exp in expenses_to_remove
                                                            if exp.okticket_expense_id])
        expenses_to_remove.unlink()

        for expense_ext_vals in backend_adapter.search(filters):
            # Map to odoo data
            internal_data = mapper.map_record(expense_ext_vals).values()
            # Searchs if the OkTicket id already exists in odoo
            binding = binder.to_internal(expense_ext_vals.get('_id'))

            if binding:
                # If exists, we update it
                binding.write(internal_data)
            else:
                values = internal_data.keys()
                required_fields_not_accomplished = []
                for req_field in required_fields:
                    if req_field not in values:
                        required_fields_not_accomplished.append(req_field)
                if required_fields_not_accomplished:
                    msg = _('Importing expense ID: %s. It does not have required fields: %s') \
                          % (expense_ext_vals.get('_id'), required_fields_not_accomplished)
                    # Log event
                    log_vals = {
                        'backend_id': self.backend_record.id,
                        'type': 'warning',
                        'msg': msg,
                    }
                    self.env['log.event'].add_event(log_vals)
                    msg = _('\nError: ') + msg
                    _logger.error(msg)
                    continue
                else:
                    binding = self.model.create(internal_data)
            okticket_hr_expense_ids.append(binding.id)
            # Finally, we bind both, so the next time we import
            # the record, we'll update the same record instead of
            # creating a new on
            binder.bind(expense_ext_vals.get('_id'), binding)
            _logger.info('Imported')
        _logger.info(
            'Import from Okticket DONE')
        return okticket_hr_expense_ids
