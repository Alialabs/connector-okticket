# -*- coding: utf-8 -*-
#
#    Created on 8/07/19
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


from odoo import api, fields, models
from odoo.addons.queue_job.job import job
from odoo.addons.component.core import Component
import logging

_logger = logging.getLogger(__name__)


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def _okticket_accounted_expense(self, new_state=True):
        '''
        Set accounted field in OkTicket expense
        '''
        self.env['okticket.hr.expense'].sudo().set_accounted_expense(self, new_state=new_state)
        # self.env['okticket.hr.expense'].sudo().write_expense(self) # TODO write para futuras operaciones de modificaciones

    def _okticket_remove_expense(self):
        self.env['okticket.hr.expense'].sudo().remove_expense(self)
        return True
        # self.env['okticket.hr.expense'].remove_expense(self)

    # @api.multi
    # def add_as_sale_order_lines(self):
    #     '''
    #     Añade la lista de hr.expense como sale.order.line al sale.order relacionado (si existe)
    #     con cada hr.expense
    #     '''
    #     for expense in self:



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def prepare_sale_order_line(self, vals):
        return {
            'display_type': vals.get('display_type'),
            'sequence': 'sequence' in vals and vals['sequence'] or 0,
            'qty_delivered_manual': 'qty_delivered_manual' in vals and vals['qty_delivered_manual'] or 0,
            'product_uom_qty': 'product_uom_qty' in vals and vals['product_uom_qty'] or 0,
            'qty_delivered': 'qty_delivered' in vals and vals['qty_delivered'] or 0,
            'price_unit': 'price_unit' in vals and vals['price_unit'] or 0,
            'discount': 'discount' in vals and vals['discount'] or 0,
            'customer_lead': 'customer_lead' in vals and vals['customer_lead'] or 0,
            'product_id': 'product_id' in vals and vals['product_id'] or 0,
            'product_uom': 'product_uom' in vals and vals['product_uom'] or 0,
            'tax_id': vals.get('tax_id', []),
            'analytic_tag_ids': vals.get('analytic_tag_ids', []),
            'name': 'name' in vals and vals['name'] or 'noName',
            'invoice_lines': vals.get('invoice_lines', []),
            'product_no_variant_attribute_value_ids': vals.get('product_no_variant_attribute_value_ids', []),
            'order_id': 'order_id' in vals and vals['order_id'] or 0,
        }

class OkticketHrExpense(models.Model):
    _inherit = 'okticket.hr.expense'

    # # TODO : refactorizar exporter con listener y adapter.CRUD (ejemplo a partir de connector_magento_export_partner/models/partner/listener
    # @job
    # @api.multi
    # def write_expense(self, expense):
    #     # Default okticket.backend ( si el user es admin, no funciona el metodo anterior de obtención de backend)
    #     backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
    #     if backend:
    #         with backend.work_on(self._name) as work:
    #             exporter = work.component(usage='hr.expense.exporter')
    #             try:
    #                 return exporter.write_expense(expense)
    #             except Exception as e:
    #                 _logger.error('Exception: %s\n', e)
    #                 import traceback
    #                 traceback.print_exc()
    #                 raise Warning(_('Could not connect to Okticket'))
    #     else:
    #         _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
    #                         self.env.user.company_id.name, self.env.user.company_id.id)

    @job
    @api.multi
    def set_accounted_expense(self, expense, new_state=True):
        # Default okticket.backend ( si el user es admin, no funciona el metodo anterior de obtención de backend)
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='hr.expense.exporter')
                try:
                    return exporter.set_accounted_expense(expense, new_state=new_state)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning(_('Could not connect to Okticket'))
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)

    @job
    @api.multi
    def remove_expense(self, expense):
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='hr.expense.exporter')
                try:
                    return exporter.remove_expense(expense)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning(_('Could not connect to Okticket'))
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)


class HrExpenseAdapter(Component):
    _inherit = 'okticket.expense.adapter'
    _collection = 'okticket.backend'

    def write_expense(self, external_expense_id, vals_dict):
        if self._auth():
            result = self.okticket_write_expense_api(external_expense_id, vals_dict)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    def remove_expense(self, external_expense_id):
        if self._auth():
            result = self.okticket_api_remove_expense(external_expense_id)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de unlink
    def okticket_write_expense_api(self, external_expense_id, vals_dict):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/expenses')
        url = url + '/' + external_expense_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        response = okticketapi.general_request(url, "PATCH", vals_dict, headers=header, only_data=False,
                                               https=self.collection.https)
        return response

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de unlink
    def okticket_api_remove_expense(self, external_expense_id):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/expenses')
        url = url + '/' + external_expense_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        return okticketapi.general_request(url, "DELETE", {}, headers=header, only_data=False,
                                               https=self.collection.https)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: