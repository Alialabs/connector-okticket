# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import fields, models, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    def _grouping_configuration_dict(self):
        """
        Dict with key:
         -'expense_sheet_grouping_method' selected
        Values, tuple with:
         - expenses classification method
         - expense sheets manage method based on data structure used in related expenses classification method
        """
        return {
            'analytic': ('analytic_classification_method', 'analytic_expense_sheet_manage_method'),
        }

    def get_expense_sheet_classification_method(self):
        """
        Return expenses classification method based on expense_sheet_grouping_method selected
        """
        grouping_method = self.backend_record.company_id.expense_sheet_grouping_method
        conf_dict = self._grouping_configuration_dict()
        classification_method = grouping_method in conf_dict and \
                                conf_dict[grouping_method] and conf_dict[grouping_method][0] or False
        if hasattr(self, classification_method) and callable(getattr(self, classification_method)):
            return getattr(self, classification_method)
        raise NotImplementedError('Function %s is not implemented', classification_method)

    def get_expense_sheet_manage_method(self):
        """
        Return expenses manage method based on expense_sheet_grouping_method selected
        """
        grouping_method = self.backend_record.company_id.expense_sheet_grouping_method
        conf_dict = self._grouping_configuration_dict()
        manage_method = grouping_method in conf_dict and \
                        conf_dict[grouping_method] and len(conf_dict[grouping_method]) > 1 \
                        and conf_dict[grouping_method][1] or False
        if hasattr(self, manage_method) and callable(getattr(self, manage_method)):
            return getattr(self, manage_method)
        raise NotImplementedError('Function %s is not implemented', manage_method)

    def analytic_classification_method(self, expense_ids):
        """
        Classifies expenses based on analytic account, payment mode and employee
        :param expense_ids: list of okticket expense ids
        """
        # expenses_grouped_dict = {
        # 'to_create': {
        #       (analytic account id, employee id, payment mode): [expense_ids]
        #   }
        # 'to_update': {
        #       expense_sheet_id: [expense_ids]
        #   }
        # }
        expenses_grouped_dict = {
            'to_create': {},
            'to_update': {}
        }

        for expense in [rel.odoo_id for rel in self.env['okticket.hr.expense'].search([('id', 'in', expense_ids)])
                        if rel.odoo_id.analytic_account_id]:  # Solo gastos con cuenta analítica

            new_expense_sheet = True
            for expense_sheet in self.env['hr.expense.sheet'].search(
                    [('state', 'in', ['draft']), ('payment_mode', '=', expense.payment_method),
                     ('employee_id', '=', expense.employee_id.id),
                     ('analytic_ids', '=', expense.analytic_account_id.id)]):

                if expense_sheet.id not in expenses_grouped_dict['to_update'].keys():
                    expenses_grouped_dict['to_update'][expense_sheet.id] = []
                expenses_grouped_dict['to_update'][expense_sheet.id].append(expense.id)
                new_expense_sheet = False
                break

            if new_expense_sheet:
                dict_key = (expense.analytic_account_id.id, expense.employee_id.id, expense.payment_mode)
                if dict_key not in expenses_grouped_dict['to_create'].keys():
                    expenses_grouped_dict['to_create'][dict_key] = []
                expenses_grouped_dict['to_create'][dict_key].append(expense.id)

        return expenses_grouped_dict

    def analytic_expense_sheet_manage_method(self, expenses_grouped_dict):
        """
        Manages classified expenses for expense sheet creation
        """
        expense_sheet_obj = self.env['hr.expense.sheet']
        # Actualización de hojas de gastos existentes
        for expense_sheet_id, expense_ids in expenses_grouped_dict['to_update'].items():
            self.env['hr.expense.sheet'].browse(expense_sheet_id).write(
                {'expense_line_ids': [(4, exp_id) for exp_id in expense_ids]})
        # Creación de nuevas hojas de gastos
        for tuple_key, expense_ids in expenses_grouped_dict['to_create'].items():
            analytic = self.env['account.analytic.account'].browse(tuple_key[0])
            employee_id = tuple_key[1]
            payment_mode = tuple_key[2]
            new_expense_sheet_values = expense_sheet_obj.prepare_expense_sheet_values(employee_id, expense_ids,
                                                                                      payment_mode, analytic)
            expense_sheet_obj.create_expense_sheet_from_analytic_partner(analytic, new_expense_sheet_values)

    # Refactorización del método run para optimizar la sobreescritura en el addon
    # okticket_connector_hr_expense_sheet_grouping

    # def run(self, filters=None, options=None):
    #     okticket_hr_expense_ids = super(HrExpenseBatchImporter, self).run(filters=filters, options=options)
    #     expense_sheet_dict = {}
    #     for expense in [rel.odoo_id for rel in
    #                     self.env['okticket.hr.expense'].search([('id', 'in', okticket_hr_expense_ids)])]:
    #         if expense.analytic_account_id:
    #             expense_sheet = False
    #             for analytic_expense_sheet in expense.analytic_account_id.expense_sheet_ids:
    #                 # Expense sheet based on state, payment mode and employee
    #                 if self.check_selected_expense_sheet(analytic_expense_sheet, expense, expense_sheet_dict):
    #                     expense_sheet = analytic_expense_sheet
    #                     break
    #             if not expense_sheet:
    #                 self.env['hr.expense.sheet'].create_expense_sheet_from_analytic_partner(expense.analytic_account_id,
    #                                                                                         expense)
    #     for sheet_id, sheet_values in expense_sheet_dict.items():  # Okticket expense sheet synchronization
    #         exp_list = sheet_values.get('expense_list', [])
    #         sheet_to_updt = self.env['hr.expense.sheet'].browse(sheet_id)
    #         expenses_to_link = [(4, exp_id) for exp_id in exp_list]
    #         sheet_to_updt.write({'expense_line_ids': expenses_to_link, })
    #     return okticket_hr_expense_ids

    def run(self, filters=None, options=None):
        okticket_hr_expense_ids = super(HrExpenseBatchImporter, self).run(filters=filters, options=options)
        self.expense_sheet_processing(okticket_hr_expense_ids)
        return okticket_hr_expense_ids

    def expense_sheet_processing(self, okticket_hr_expense_ids):
        """
        Expense classification and expense sheet creation/modification based on
        grouping method selected in current company
        :param okticket_hr_expense_ids: list of int (hr.expense ids)
        """
        # 1º) Clasificación de gastos en base al método de agrupación indicado
        expense_classification_method = self.get_expense_sheet_classification_method()
        expense_classification = expense_classification_method(okticket_hr_expense_ids)
        # Retorna una estructura de datos que el método de gestión de hojas de gasto es capaz de manejar
        expense_manage_method = self.get_expense_sheet_manage_method()
        expense_manage_method(expense_classification)
        return True


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    analytic_ids = fields.Many2many('account.analytic.account',
                                    'analytic_expense_sheet_rel',
                                    'sheet_id', 'analytic_id')

    def prepare_expense_sheet_values(self, employee_id, expense_ids, payment_mode, analytic):
        """
        :param analytic: browse account.analytic.account
        :param employee_id: int hr.employee id
        :param expense_ids: list of int (expense ids)
        :param payment_mode: str
        """
        sale_order = analytic.get_related_sale_order()
        analytic_name = analytic and analytic.name or 'NO CostCenter'
        if sale_order and sale_order.partner_id and sale_order.partner_id.name:
            complete_name = '-'.join([sale_order.partner_id.name, analytic_name])
        else:
            complete_name = analytic_name  # Sin cliente
        return {
            'name': complete_name,
            'employee_id': employee_id,
            'expense_line_ids': [(4, exp_id) for exp_id in expense_ids],
            'analytic_ids': [(4, analytic.id)],
            'user_id': sale_order and sale_order.user_id and sale_order.user_id.id or False,
            'payment_mode': payment_mode,
        }

    def create_expense_sheet_from_analytic_partner(self, analytic, sheet_values):
        """
        Creates new hr.expense.sheet from analytic and sheet_values data
        :param analytic: browse account.analytic.account
        :param sheet_values: dict for hr.expense.sheet creating
        :return: new hr.expense.sheet
        """
        new_expense_sheet = False
        if analytic and sheet_values:
            _logger.debug("Creating expense sheet for account ID: " + str(analytic.id))
            new_expense_sheet = self.create(sheet_values)
        else:
            _logger.error("Error in expense sheet create process")
            msg = "Error in expense sheet create process" + \
                  "Account ID: " + analytic.id
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
