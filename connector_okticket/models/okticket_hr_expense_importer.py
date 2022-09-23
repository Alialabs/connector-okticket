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
        return {'unit_amount': record['amount']}

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
        if 'name' in record:  # and 'type_id' in record and record['type_id'] == 1:
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
        # Si el método de pago es 'efectivo', el modo de pago es 'pagado por el empleado'
        # En caso contrario, es 'pagado por la empresa'
        # Si existe campo 'refundable' en 'custom_fields', se evalúa para asignar 'pagado por la empresa'
        payment_mode = 'payment_method' in record and record['payment_method'] == 'efectivo' and 'own_account' \
                       or 'company_account'

        if record.get('custom_fields') and record['custom_fields'].get('refundable'):
            payment_mode = 'own_account'  # Pago por cliente ('refundable' == 'refund')
            if record['custom_fields']['refundable'] == 'payed':
                payment_mode = 'company_account'  # Pago por empresa

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
        okticket_account_id = False
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
        backend_adapter = self.component(usage='backend.adapter')
        okticket_hr_expense_ids = []
        mapper = self.component(usage='importer')
        binder = self.component(usage='binder')

        # Fields needed to be able to import a expense
        required_fields = ['product_id', 'employee_id', 'company_id']

        filters, last_expenses_import = self.datetime_expenses_import_backend_filter(filters)
        only_reviewed = self.backend_record.import_only_reviewed_expenses

        for expense_ext_vals in backend_adapter.search(filters):

            # Searchs if the OkTicket id already exists in odoo
            binding = binder.to_internal(expense_ext_vals.get('_id'))

            # Gasto eliminado (lógico) en Okticket
            if 'deleted_at' in expense_ext_vals and expense_ext_vals['deleted_at']:  # deleted_at not null
                if binding:
                    self.delete_expense_synchro(binding)
                continue

            # Restricción de importación de gastos revisados
            if only_reviewed and expense_ext_vals and 'review' not in expense_ext_vals:
                continue

            # Map to odoo data
            internal_data = mapper.map_record(expense_ext_vals).values()

            if binding:
                # If exists, we update it  # TODO analizar error employee_id
                # del internal_data['backend_id']
                # del internal_data['external_id']
                # self.env['hr.expense'].browse(binding.odoo_id.id).write(internal_data)
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

        # Actualizar fecha de última importación de gastos
        self.backend_record.import_expenses_since = last_expenses_import
        return okticket_hr_expense_ids

    def delete_expense_synchro(self, binding):
        """
        Tries to unlink Odoo expense if it was deleted (logically) in Okticket.
        If it couldn't be possible, a "deleted in Okticket" flag is actived in the expense. Odoo will try deleted the
        expenses with this flag active when it could be possible (state changes in expense sheets).
        :param binding:
        """
        try:
            binding.odoo_id.unlink()  # Se trata de eliminar el gasto en Odoo
        except Exception as e:
            # Se marca como "gasto eliminado en Okticket" y se registra el evento
            binding.odoo_id.okticket_deleted = True
            msg = _('\nError while try to unlink expense %s in Odoo: %s') % (binding.odoo_id.id, e)
            # Log event
            log_vals = {
                'backend_id': self.backend_record.id,
                'type': 'warning',
                'msg': msg,
            }
            self.env['log.event'].add_event(log_vals)
            _logger.error(msg)

    def datetime_expenses_import_backend_filter(self, filters):
        """
        Manages datetime last expenses import backend param to be added in update_after API-REST request
        :param filters: searching filters dict
        :return: filters dict, last import datetime
        """
        last_expenses_import = datetime.datetime.now()
        if not self.backend_record.ignore_import_expenses_since and self.backend_record.import_expenses_since:
            # Restricción de importación de gastos por fecha de última importación
            filters = filters or {}
            filters.update({
                'params': {
                    'updated_after': self.backend_record.import_expenses_since.strftime("%Y-%m-%dT%H:%M:%S")
                }
            })
        else:
            # All expenses not in "sent" state (this is, state = "draft") are eliminated before new import or
            # synchronization of expenses from OkTicket. This way, we ensure Odoo-OkTicket synchronization.
            states_to_remove = ['draft']
            expenses_to_remove = self.env['hr.expense'].search([('state', 'in', states_to_remove)])
            expenses_to_remove = self.env['hr.expense'].browse([exp.id for exp in expenses_to_remove
                                                                if exp.okticket_expense_id])
            expenses_to_remove.unlink()
        return filters, last_expenses_import
