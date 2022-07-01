# -*- coding:utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    ### Métodos que recopilan la relación entre el estado del campo y las funciones de clasificación ###
    def _grouping_configuration_dict(self):
        """
        Dict with key:
         -'expense_sheet_grouping_method' selected
        Values, tuple with:
         - expenses classification method
        """
        return {
            'analytic': 'analytic_classification_method',
        }

    def _time_grouping_configuration_dict(self):
        """
        Dict with key:
         -'expense_sheet_grouping_time' selected
        Values, tuple with:
         - expenses grouped by classification method based on interval time selected
        """
        return {
            'no_interval': 'expenses_by_no_interval_time_method',
        }

    ### Métodos para recuperar dinámicamente la función correspondiente al estado actual ###
    def get_expense_sheet_classification_method(self):
        """
        Return expenses classification method based on expense_sheet_grouping_method selected
        """
        grouping_method = self.backend_record.company_id.expense_sheet_grouping_method
        conf_dict = self._grouping_configuration_dict()
        classification_method = grouping_method in conf_dict and \
                                conf_dict[grouping_method] or False
        if hasattr(self, classification_method) and callable(getattr(self, classification_method)):
            return getattr(self, classification_method)
        raise NotImplementedError('Function %s is not implemented', classification_method)

    def get_expense_sheet_grouping_time_method(self):
        """
        Returns a method to group expenses by a specified time interval
        """
        grouping_method = self.backend_record.company_id.expense_sheet_grouping_time
        conf_dict = self._time_grouping_configuration_dict()
        time_method = grouping_method in conf_dict and conf_dict[grouping_method] or False
        if hasattr(self, time_method) and callable(getattr(self, time_method)):
            return getattr(self, time_method)
        raise NotImplementedError('Function %s is not implemented', time_method)

    ### Funciones de clasificación de gastos ###
    def analytic_classification_method(self, expense_ids):
        """
        Classifies expenses based on analytic account, payment mode and employee
        :param expense_ids: list of okticket expense ids
        :return Grouped expenses structure
        """
        grouped_expenses = [
            # Por cada expense se genera esta estructura donde las key de group_fields son campos de hr.expense.sheet
            # {
            #     'group_fields': {
            #         'employee_id': expense.employee_id and expense.employee_id.id,
            #         'payment_mode': expense.payment_mode,
            #         'analytic_ids': expense.analytic_account_id.id,
            #     },
            #     'expense': expense,
            # }
        ]
        for expense in self.env['hr.expense'].browse(expense_ids):
            grouped_expenses.append({
                'group_fields': {
                    'employee_id': expense.employee_id and expense.employee_id.id,
                    'payment_mode': expense.payment_mode,
                    'analytic_ids': expense.analytic_account_id and expense.analytic_account_id.id,
                },
                'expense': expense,
            })
        return grouped_expenses

    ### Funciones de clasificación de gastos por intervalo temporal ###
    def expenses_by_no_interval_time_method(self, grouped_expenses):
        """
        No action needed
        """
        return grouped_expenses

    ### Funciones de clasificación de gastos por intervalo temporal ###
    def grouped_expenses_managing(self, grouped_expenses):
        """
        Creates/updates hr.expense.sheet based on grouped_expenses data classification.
        :param grouped_expenses: list of dict with 'group_fields' dict with key hr.expense.sheet field and value
        """
        hr_expense_sheet_obj = self.env['hr.expense.sheet']
        for expense_data in grouped_expenses:

            # Search domain
            sheet_domain = []
            for sheet_field, sheet_value in expense_data['group_fields'].items():
                sheet_domain.append((sheet_field, '=', sheet_value))

            # Expense sheet values
            expense_sheet_values = {
                'expense_line_ids': [(4, expense_data['expense'].id)],
            }
            # TODO desacoplar esta asignación!!
            if 'analytic_ids' in expense_data['group_fields'] and expense_data['group_fields']['analytic_ids']:
               expense_sheet_values.update({
                   'analytic_ids': [(4, expense_data['group_fields']['analytic_ids'])]
               })

            hr_expense_sheet = hr_expense_sheet_obj.search(sheet_domain)
            if hr_expense_sheet:  # Update
                hr_expense_sheet.write(expense_sheet_values)
            else:  # Create
                new_sheet_values = {}
                for sheet_field, sheet_value in expense_data['group_fields'].items():
                    if sheet_field not in new_sheet_values:
                        new_sheet_values[sheet_field] = sheet_value

                # Prepare para generar campos required como name
                new_sheet_values = hr_expense_sheet_obj.prepare_expense_sheet_values(new_sheet_values)
                if new_sheet_values and 'name' in new_sheet_values and not new_sheet_values['name']:
                    new_sheet_values['name'] = expense_data['expense'].analytic_account_id and \
                                               expense_data[
                                                   'expense'].analytic_account_id.name or 'NO-ANALYTIC-FOUND'

                new_sheet_values.update(expense_sheet_values)

                # TODO es necesario un prepare dinámico vinculado con los tipos de agrupación (normal y temporal)
                #  para poder generar aquí un dict con operadores (para fechas)
                #  o para campos x2Many (analytic_ids 'in')
                #  o para el caso del payment_mode que lo coge dinámicamente la hoja de gastos

                hr_expense_sheet_obj.create(new_sheet_values)

    ### Función de importación de gastos ###
    def run(self, filters=None, options=None):
        """
        Imports expenses from Okticket and it classify them in expense sheets
        """
        okticket_hr_expense_ids = super(HrExpenseBatchImporter, self).run(filters=filters, options=options)
        self.expense_sheet_processing(okticket_hr_expense_ids)
        return okticket_hr_expense_ids

    ### Función donde se recuperan dinámicamente las funciones de
    # clasificación, división por intervalo temporal y agrupación en hojas de gastos de gastos ###

    def expense_sheet_processing(self, okticket_hr_expense_ids):
        """
        Expense classification and expense sheet creation/modification based on
        grouping method and time interval selected in current company
        :param okticket_hr_expense_ids: list of int (hr.expense ids)
        """
        # 1º) Clasificación de gastos en base al método de agrupación indicado
        # Retorna una estructura de datos que el método de gestión de hojas de gasto es capaz de manejar
        expense_classification_method = self.get_expense_sheet_classification_method()
        # Recupera hr.expenses relacionados con los gastos de okticket. Solo aquellos con cuenta anlítica
        hr_expense_ids = [rel.odoo_id.id for rel in self.env['okticket.hr.expense'].search([
            ('id', 'in', okticket_hr_expense_ids)])]
        grouped_expenses = expense_classification_method(hr_expense_ids)

        # 2º) Reclasificación en base a parámetros temporales
        expense_time_interval_method = self.get_expense_sheet_grouping_time_method()
        grouped_expenses = expense_time_interval_method(grouped_expenses)

        # 3º) Creación/actualización de hojas de gasto
        self.grouped_expenses_managing(grouped_expenses)

        return True


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    analytic_ids = fields.Many2many('account.analytic.account',
                                    'analytic_expense_sheet_rel',
                                    'sheet_id', 'analytic_id')

    def check_empty_sheet(self):
        """
        If sheet is empty, delete it
        """
        self.filtered(lambda x: not x.expense_line_ids).unlink()

    def write(self, vals):
        """
        Removes empty expense sheets
        """
        result = super(HrExpenseSheet, self).write(vals)
        if vals and 'expense_line_ids' in vals:
            self.check_empty_sheet()
        return result

    def prepare_expense_sheet_values(self, raw_values):
        complete_name = raw_values and 'name' in raw_values and raw_values['name'] or 'NO-ANALYTIC-FOUND'

        employee_id = raw_values['employee_id']
        analytic = 'analytic_ids' in raw_values and raw_values['analytic_ids'] and \
                   self.env['account.analytic.account'].browse(raw_values['analytic_ids']) or False
        payment_mode = raw_values['payment_mode']
        sale_order = False

        if analytic:
            sale_order = analytic.get_related_sale_order()
            analytic_name = analytic and analytic.name or 'NO CostCenter'
            if sale_order and sale_order.partner_id and sale_order.partner_id.name:
                complete_name = '-'.join([sale_order.partner_id.name, analytic_name])
            else:
                complete_name = analytic_name  # Sin cliente
        raw_values.update({
            'name': complete_name,
            'employee_id': employee_id,
            'user_id': sale_order and sale_order.user_id and sale_order.user_id.id or False,
            'payment_mode': payment_mode,
        })
        return raw_values

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
