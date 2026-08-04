from odoo import fields, models, _
from odoo.addons.component.core import Component


class HrExpense(models.Model):
    _inherit = 'hr.expense'
    _description = 'HR Expense'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='odoo_id',
        string='OkTicket Expense Bindings'
    )

    okticket_expense_id = fields.Char(
        string="OkTicket ID",
        compute='_compute_okticket_expense_id',
        inverse='_inverse_okticket_expense_id',
        search='_search_okticket_expense_id'
    )

    def _compute_okticket_expense_id(self):
        for expense in self:
            expense.okticket_expense_id = (
                expense.okticket_bind_ids[0].external_id if expense.okticket_bind_ids else '-1'
            )

    def _inverse_okticket_expense_id(self):
        for exp in self.filtered(lambda ex: ex.okticket_bind_ids):
            exp.okticket_bind_ids.write({'external_id': exp.okticket_expense_id})

    def _search_okticket_expense_id(self, operator, value):
        # Odoo 19 normalizes '='/'!=' into 'in'/'not in' before calling field search
        if operator in ('=', '!='):
            operator = 'in' if operator == '=' else 'not in'
            value = [value]
        if operator not in ('in', 'not in'):
            raise ValueError(_('This operator is not supported'))
        odoo_ids = self.env['okticket.hr.expense'].search([
            ('external_id', 'in', list(value))]).mapped('odoo_id').ids
        return [('id', 'not in' if operator == 'not in' else 'in', odoo_ids)]


class OkticketExpense(models.Model):
    _name = 'okticket.hr.expense'
    _description = 'Okticket HR Expense Binding'

    _inherit = 'okticket.binding'
    _inherits = {'hr.expense': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='hr.expense',
        string='Expense',
        required=True,
        ondelete='cascade'
    )

    def import_expenses_since(self, backend, since_date=None, **kwargs):
        # Reasignar el contexto para incluir la compañía
        self = self.with_company(self.backend_record.company_id)

        # Llamar al método import_batch con el contexto actualizado
        self.env['okticket.hr.expense'].sudo().with_context(company_id=backend.company_id.id).import_batch(backend,
                                                                                                           priority=5)
        return True


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    okticket_hr_expense_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='backend_id',
        string='HR Expense Bindings',
        context={'active_test': False}
    )


class ExpensesAdapter(Component):
    """
    Expenses Backend Adapter for Okticket

    Expenses in Okticket cannot be queried by the date of creation
    or update. The alternative is to search for all entries for a
    period of time and then filter these by the field updated_on.
    """
    _name = 'okticket.expense.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.hr.expense'

    def search(self, filters=False):
        if not self._auth():
            return []

        params_dict = {'accounted': 'false', 'statuses': '0,1,2'}

        if filters and 'params' in filters and isinstance(filters['params'], dict):
            params_dict.update(filters['params'])

        if filters and filters.get('expense_external_id'):
            result = self.okticket_api.find_expense_by_id(
                filters['expense_external_id'], https=self.collection.https
            )
        else:
            result = self.okticket_api.find_expenses(
                params=params_dict, https=self.collection.https
            )

        result['log'].update({
            'backend_id': self.backend_record.id,
            'type': result['log'].get('type') or 'success',
        })
        self.env['log.event'].add_event(result['log'])

        if isinstance(result['result'], bool):
            return []

        expenses = result['result']
        # find_expense_by_id returns a single record instead of a list
        if isinstance(expenses, dict):
            expenses = expenses.get('data', expenses)
        if isinstance(expenses, dict):
            expenses = [expenses]
        return expenses
