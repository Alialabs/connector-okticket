# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _
from odoo.addons.component.core import Component


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='odoo_id',
        string='OkTicket Expense Bindings')

    def _get_expense_okticket_id(self):
        for expense in self:
            expense.okticket_expense_id = expense.okticket_bind_ids and \
                                          expense.okticket_bind_ids[0].external_id or '-1'

    def _set_expense_okticket_id(self):
        for exp in self.filtered(lambda ex: ex.okticket_bind_ids):
            exp.okticket_bind_ids.write({'external_id': exp.okticket_expense_id})

    def _search_expense_okticket_id(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, str):
            raise ValueError(_('Value should be string (not %s)'), value)
        domain = []
        odoo_ids = self.env['okticket.hr.expense'].search([('external_id', operator, value)]).mapped('odoo_id').ids
        if odoo_ids:
            domain.append(('id', 'in', odoo_ids))
        return domain

    okticket_expense_id = fields.Char(string="OkTicket id",
                                      compute=_get_expense_okticket_id,
                                      inverse=_set_expense_okticket_id,
                                      search=_search_expense_okticket_id)


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


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    okticket_hr_expense_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='backend_id',
        string='Hr Expense Bindings',
        context={'active_test': False})


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

            # Si el resultado es un valor True / False (control de errores que no interrumpen ejecución, ej.: 422)
            if isinstance(result['result'], bool):
                return []

            return result['result']
        return []
