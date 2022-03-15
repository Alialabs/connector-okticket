# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models
from odoo.addons.component.core import Component


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='odoo_id',
        string='OkTicket Expense Bindings',
        readonly=True,
    )

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
            if filters and filters.get('expense_external_id'):
                result = self.okticket_api.find_expense_by_id(filter['expense_external_id'],
                                                              https=self.collection.https)
            else:
                result = self.okticket_api.find_expenses(params={
                    'accounted': 'false',
                    'statuses': '0,1,2'},
                    https=self.collection.https)

            # Log event
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return []
