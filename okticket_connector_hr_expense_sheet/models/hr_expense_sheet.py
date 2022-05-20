# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import fields, models, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    def check_selected_expense_sheet(self, analytic_expense_sheet, expense, expense_sheet_dict):
        """
        Checks if the expense sheet is valid for the new expense.
        It should be in draft state, has the same pay mode and the same employee
        """
        if analytic_expense_sheet.state in ['draft'] and \
                (not analytic_expense_sheet.payment_mode or
                 expense.payment_mode == analytic_expense_sheet.payment_mode) and \
                expense.employee_id.id == analytic_expense_sheet.employee_id.id and \
                (analytic_expense_sheet.id not in expense_sheet_dict or
                 expense_sheet_dict[analytic_expense_sheet.id]['payment_mode'] == expense.payment_mode):
            if analytic_expense_sheet.id not in expense_sheet_dict:
                expense_sheet_dict[analytic_expense_sheet.id] = {
                    'expense_list': [],
                    'payment_mode': expense.payment_mode,
                }
            expense_sheet_dict[analytic_expense_sheet.id]['expense_list'].append(expense.id)
            return True
        return False

    def run(self, filters=None, options=None):
        okticket_hr_expense_ids = super(HrExpenseBatchImporter, self).run(filters=filters, options=options)
        expense_sheet_dict = {}
        for expense in [rel.odoo_id for rel in
                        self.env['okticket.hr.expense'].search([('id', 'in', okticket_hr_expense_ids)])]:
            if expense.analytic_account_id:
                expense_sheet = False
                for analytic_expense_sheet in expense.analytic_account_id.expense_sheet_ids:
                    # Expense sheet based on state, payment mode and employee
                    if self.check_selected_expense_sheet(analytic_expense_sheet, expense, expense_sheet_dict):
                        expense_sheet = analytic_expense_sheet
                        break
                if not expense_sheet:
                    self.env['hr.expense.sheet'].create_expense_sheet_from_analytic_partner(expense.analytic_account_id,
                                                                                            expense)
        for sheet_id, sheet_values in expense_sheet_dict.items():  # Okticket expense sheet synchronization
            exp_list = sheet_values.get('expense_list', [])
            sheet_to_updt = self.env['hr.expense.sheet'].browse(sheet_id)
            expenses_to_link = [(4, exp_id) for exp_id in exp_list]
            sheet_to_updt.write({'expense_line_ids': expenses_to_link, })
        return okticket_hr_expense_ids


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    analytic_ids = fields.Many2many('account.analytic.account',
                                    'analytic_expense_sheet_rel',
                                    'sheet_id', 'analytic_id')

    def create_expense_sheet_from_analytic_partner(self, analytic, expense):
        """
        Creates new hr.expense.sheet from analytic and expense data
        :param analytic: browse account.analytic.account
        :param expense: browse hr.expense
        :return: new hr.expense.sheet
        """
        _logger.debug("Account ID: " + expense.analytic_account_id.name + " - Expense ID: " + str(
            expense.id) + " - Expense OkTicket-ID: " + expense.okticket_expense_id)
        new_expense_sheet = False
        if analytic and expense:
            sale_order = analytic.get_related_sale_order()
            analytic_name = analytic and analytic.name or 'NO CostCenter'
            if sale_order and sale_order.partner_id and sale_order.partner_id.name:
                complete_name = '-'.join([sale_order.partner_id.name, analytic_name])
            else:
                complete_name = analytic_name  # Sin cliente
            sheet_vals = {
                'name': complete_name,
                'employee_id': expense.employee_id and expense.employee_id.id or False,
                'expense_line_ids': [(4, expense.id)],
                'analytic_ids': [(4, analytic.id)],
                'user_id': sale_order and sale_order.user_id and sale_order.user_id.id or False,
                'payment_mode': expense.payment_mode,
            }
            new_expense_sheet = self.create(sheet_vals)
        else:
            _logger.error("Error in expense sheet create process")
            msg = "Error in expense sheet create process" + \
                  "Account ID: " + expense.analytic_account_id.name + " - Expense ID: " + \
                  str(expense.id) + " - Expense OkTicket-ID: " + expense.okticket_expense_id
            event = {
                'backend_id': self.env['okticket.backend'].search([('active', '=', True)], limit=1).id,
                'type': 'error',
                'tag': 'OP',
                'msg': msg,
            }
            self.env['log.event'].add_event(event)
        return new_expense_sheet

    def action_submit_sheet(self):
        """
        "Send to responsable"
        Implied actions:
            - Set 'accounted' = 'true' in expenses from Okticket expense sheet.
            - Action [347] Okticket
        """
        super(HrExpenseSheet, self).action_submit_sheet()
        for expense in self.expense_line_ids:
            expense._okticket_accounted_expense(new_state=True)  # 'accounted': 'True'
        action_id = 347
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    def reset_expense_sheets(self):
        """
        From "Enviada" and "Rechazada" state: "Cambiar a borrador"/"Reabrir(Empleado)"
        From "Aprobada" state: "Rechazada" + "Cambiar a borrador"/"Reabrir(Empleado)"
        Implied actions:
            - Set 'accounted' = 'false' in expenses from Okticket expense sheet.
            - Action [352] Okticket from "Aprobada" to "Rechazada" state
            - Action [348] Okticket from "Enviada" state
            - Action [354] Okticket from "Rechazada" state
        """

        if self.state == 'approve':
            self.refuse_sheet('')

        if self.state == 'cancel':
            action_id = 354  # From "Rechazada"
        elif self.state == 'submit':
            action_id = 348  # From "Enviada"

        if super(HrExpenseSheet, self).reset_expense_sheets():
            for expense in self.expense_line_ids:
                expense._okticket_accounted_expense(new_state=False)
            self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    def refuse_sheet(self, reason):
        """
        From "Enviada" and "Aprobada" state: "Rechazar"/"Rechazar(Admin)"
        Implied actions:
            - Set'accounted' = 'false' in expenses from Okticket expense sheet.
            - Action [350] Okticket from "Enviada" state
            - Action [352] Okticket from "Aprobada" state
        """
        if self.state == 'approve':
            action_id = 352  # From "Aprobada"
        else:
            action_id = 350  # From "Enviada"
        super(HrExpenseSheet, self).refuse_sheet(reason)
        for expense in self.expense_line_ids:
            expense._okticket_accounted_expense(new_state=False)
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id, comments=reason)

    def approve_expense_sheets(self):
        """
        "Aprobar"/"Aprobar(Admin)"
        Implied actions:
            - Action [349] Okticket
        """
        super(HrExpenseSheet, self).approve_expense_sheets()
        # Product "expense" is included as sale.order.line in sale.order related with hr.expense
        action_id = 349
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    def action_sheet_move_create(self):
        """
        "Publicar asientos"/"Publicar asientos(Admin)"
        Implied actions:
            - Action [351] Okticket
        """
        res = super(HrExpenseSheet, self).action_sheet_move_create()
        if res:
            action_id = 351
            self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)
        return res

    def action_sheet_payment_registry(self, body):
        """
        "Registrar pago"/"Registrar pago(Admin)"
        Implied actions:
            - Action [353] Okticket
        """
        action_id = 353
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    # def action_unpost

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, body='', **kwargs):
        result = super(HrExpenseSheet, self).message_post(body=body, **kwargs)
        if result and self.env.context and self.env.context.get('okticket_synch'):
            self.action_sheet_payment_registry(body)
        return result

    def unlink(self):
        return super(HrExpenseSheet, self).unlink()


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payments(self):
        super(AccountPaymentRegister, self.with_context(
            okticket_synch=True,
        ))._create_payments()
