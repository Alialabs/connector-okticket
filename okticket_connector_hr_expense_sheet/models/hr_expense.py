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


from odoo import _, api, fields, models
from odoo.addons.component.core import Component
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def _okticket_accounted_expense(self, new_state=True):
        """
        Set accounted field in OkTicket expense
        """
        self.ensure_one()  # set_accounted_expense doesn't manage record set of multiple expenses
        self.env['okticket.hr.expense'].sudo().set_accounted_expense(self, new_state=new_state)

    # def _okticket_remove_expense(self):
    #     self.env['okticket.hr.expense'].sudo().remove_expense(self)
    #     return True

    def write(self, vals):
        sheet_to_check = False
        if vals and 'sheet_id' in vals:
            sheet_to_check = self.mapped('sheet_id')
        result = super(HrExpense, self).write(vals)
        if vals and 'sheet_id' in vals and sheet_to_check:
            sheet_to_check.check_empty_sheet()  # Comprueba si la hoja está vacía para eliminarla
        return result

    def unlink(self):
        sheet_to_check = self.mapped('sheet_id')
        result = super(HrExpense, self).unlink()
        sheet_to_check.check_empty_sheet()  # Comprueba si la hoja está vacía para eliminarla
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def prepare_sale_order_line(self, values):
        return {
            'display_type': values.get('display_type'),
            'sequence': 'sequence' in values and values['sequence'] or 0,
            'qty_delivered_manual': 'qty_delivered_manual' in values and values['qty_delivered_manual'] or 0,
            'product_uom_qty': 'product_uom_qty' in values and values['product_uom_qty'] or 0,
            'qty_delivered': 'qty_delivered' in values and values['qty_delivered'] or 0,
            'price_unit': 'price_unit' in values and values['price_unit'] or 0,
            'discount': 'discount' in values and values['discount'] or 0,
            'customer_lead': 'customer_lead' in values and values['customer_lead'] or 0,
            'product_id': 'product_id' in values and values['product_id'] or 0,
            'product_uom': 'product_uom' in values and values['product_uom'] or 0,
            'tax_id': values.get('tax_id', []),
            'analytic_tag_ids': values.get('analytic_tag_ids', []),
            'name': 'name' in values and values['name'] or 'noName',
            'invoice_lines': values.get('invoice_lines', []),
            'product_no_variant_attribute_value_ids': values.get('product_no_variant_attribute_value_ids', []),
            'order_id': 'order_id' in values and values['order_id'] or 0,
        }


class OkticketHrExpense(models.Model):
    _inherit = 'okticket.hr.expense'

    def set_accounted_expense(self, expense, new_state=True):
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
                    raise (e or UserError(_('Could not connect to Okticket')))
        else:
            _logger.warning(_('WARNING! Not exists backend for company %s (%s)'),
                            self.env.user.company_id.name, self.env.user.company_id.id)

    # @api.multi
    # def remove_expense(self, expense):
    #     backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
    #     if backend:
    #         with backend.work_on(self._name) as work:
    #             exporter = work.component(usage='hr.expense.exporter')
    #             try:
    #                 return exporter.remove_expense(expense)
    #             except Exception as e:
    #                 _logger.error('Exception: %s\n', e)
    #                 import traceback
    #                 traceback.print_exc()
    #                 raise (e or UserError(_('Could not connect to Okticket')))
    #     else:
    #         _logger.warning(_('WARNING! Not exists backend for company %s (%s)'),
    #                         self.env.user.company_id.name, self.env.user.company_id.id)


class HrExpenseAdapter(Component):
    _inherit = 'okticket.expense.adapter'
    _collection = 'okticket.backend'

    def write_expense(self, external_expense_id, vals_dict):
        if self._auth():
            result = self.okticket_write_expense_api(external_expense_id, vals_dict)
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # def remove_expense(self, external_expense_id):
    #     if self._auth():
    #         result = self.okticket_api_remove_expense(external_expense_id)
    #         # Log event
    #         result['log'].update({
    #             'backend_id': self.collection.id,
    #             'type': result['log'].get('type') or 'success',
    #         })
    #         self.env['log.event'].add_event(result['log'])
    #         return result.get('result')
    #     return False

    def okticket_write_expense_api(self, external_expense_id, vals_dict):
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

    # def okticket_api_remove_expense(self, external_expense_id):
    #     okticketapi = self.okticket_api
    #     url = okticketapi.get_full_path('/expenses')
    #     url = url + '/' + external_expense_id
    #     header = {
    #         'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
    #         'Content-Type': 'application/json',
    #     }
    #     return okticketapi.general_request(url, "DELETE", {}, headers=header, only_data=False,
    #                                        https=self.collection.https)
