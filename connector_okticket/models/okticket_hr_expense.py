# -*- coding: utf-8 -*-
#
#    Created on 16/04/19
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

from odoo import fields, models, api
from odoo.addons.component.core import Component


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='odoo_id',
        string='OkTicket Expense Bindings',
        readonly=True,
    )

    @api.multi
    def _get_external_expense(self):
        for expense in self:
            expense.okticket_expense_id = expense.okticket_bind_ids and \
                                          expense.okticket_bind_ids[0].external_id or ''

    okticket_expense_id = fields.Char(string="OkTicket id",
                                      compute=_get_external_expense,
                                      readonly=True)


class OkticketExpense(models.Model):
    _name = 'okticket.hr.expense'
    _inherit = 'okticket.binding'
    _inherits = {'hr.expense': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='hr.expense',
        string='Expense',
        required=True,
        ondelete='cascade',
    )

    @api.multi
    def import_expenses_since(self, backend, since_date=None, **kwargs):
        self.env['okticket.hr.expense'].sudo().import_batch(backend, priority=5)
        return True


class ExpensesAdapter(Component):
    """
    Expenses Backend Adapter for Okticket

    Expenses in Okticket can not be querried by the date of creation
    or update. The alternative is to search for all entries for a
    period of time and then filtering these by the field updated_on.
    """
    _name = 'okticket.expense.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.hr.expense'

    def search(self, filters=False):
        if self._auth():

            # Parámetros por defecto
            params_dict = {'accounted': 'false',
                           'statuses': '0,1,2'}

            if filters and 'params' in filters and filters['params'] and isinstance(filters['params'], dict):
                params_dict.update(filters['params'])  # Permite concatenar params a través del filters

            if filters and filters.get('expense_external_id'):
                # No se utiliza esta llamada
                result = self.okticket_api.find_expense_by_id(filters['expense_external_id'],
                                                              https=self.collection.https)
            else:
                result = self.okticket_api.find_expenses(params=params_dict,
                                                         https=self.collection.https)

            # Log event
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return []