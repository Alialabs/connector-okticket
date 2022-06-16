# -*- coding:utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import fields, models, api
from odoo.addons.component.core import Component
from odoo.addons.okticket_connector_hr_expense_sheet.models.hr_expense_grouping import ExpenseGrouping

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
         - expense sheets manage method based on data structure used in related expenses classification method
        """
        return {
            'analytic': ('analytic_classification_method', 'analytic_expense_sheet_manage_method'),
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
            'monthly': 'expenses_by_monthly_time_method',
        }

    ### Métodos para recuperar dinámicamente la función correspondiente al estado actual ###

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

    ### Funciones de clasificación de gastos ###

    def could_add_expense_to_empty_sheet_by_payment_mode(self, expense_sheet, expenses_grouped, expense):
        """
        Checks if a expense could be added in empty expense sheet before start expenses import process execution.
        Expense sheet could have expenses to be added. All expenses must have the same payment_moe
        :param expense_sheet: record
        :param expenses_grouped: object
        :param expense: record
        :return: bool
        """
        result = True
        if not expense_sheet.payment_mode:
            to_update_dict = expenses_grouped.get_to_update_dict()
            if expense_sheet.id in to_update_dict and to_update_dict[expense_sheet.id]:
                reference_sheet_expense = self.env['hr.expense'].browse(to_update_dict[expense_sheet.id][0])
                if reference_sheet_expense.payment_mode != expense.payment_mode:
                    result = False
        return result

    def analytic_classification_method(self, expenses_grouped, expense_ids, excluded_expense_sheet_ids=[]):
        """
        Classifies expenses based on analytic account, payment mode and employee
        :param expenses_grouped: ExpenseGrouping object
        :param expense_ids: list of okticket expense ids
        :param excluded_expense_sheet_ids: list of expense sheet ids to update expenses
        """
        for expense in self.env['hr.expense'].browse(expense_ids).filtered(lambda ex: ex.analytic_account_id):  # Solo gastos con cuenta analítica

            new_expense_sheet = True
            for expense_sheet in self.env['hr.expense.sheet'].search(
                    [('state', 'in', ['draft']), ('employee_id', '=', expense.employee_id.id),
                     ('id', 'not in', excluded_expense_sheet_ids),
                     ('analytic_ids', '=', expense.analytic_account_id.id)]).filtered(
                lambda exp_sheet: not exp_sheet.payment_mode or
                                  exp_sheet.payment_mode == expense.payment_mode):

                if self.could_add_expense_to_empty_sheet_by_payment_mode(expense_sheet, expenses_grouped, expense):
                    expenses_grouped.add_exp_to_update_sheet(expense_sheet.id, expense.id)
                    new_expense_sheet = False
                    break

            if new_expense_sheet:
                custom_key = (expense.analytic_account_id.id, expense.employee_id.id, expense.payment_mode)
                expenses_grouped.add_exp_to_create_by_key(custom_key, expense.id)

        return expenses_grouped

    ### Funciones de reclasificación de gastos por intervalo temporal indicado ###
    def expenses_by_no_interval_time_method(self, expenses_grouped, expense_classification_method):
        """
        No action needed
        """
        return expenses_grouped

    def reassign_expenses_for_month_classification(self, reassign_dict, expenses_grouped,
                                                   expense_classification_method):
        """
        Recursive method to search a valid expense sheet and reassign expenses
        :param reassign_dict: { expense_sheet_id_not_valid : [expenses ids to be reassigned]
        :param expenses_grouped: object
        :param expense_classification_method: dynamic classification method
        """
        for invalid_expense_sheet_id, reassign_values in reassign_dict.items():
            temp_expenses_grouped = ExpenseGrouping()  # Agrupación temporal de gastos en cada iteración
            temp_reassign_dict = {}  # Diccionario de reasignación temporal en cada iteración

            accum_no_valid_expense_sheet_ids = reassign_values['accum_no_valid_expense_sheet_ids']
            expense_to_reassign_ids = reassign_values['expenses_ids_to_reassign']

            # 1º) Lanzar de nuevo el método de clasificación de gastos con la hoja de gastos como exclusión
            expense_classification_method(temp_expenses_grouped, expense_to_reassign_ids,
                                          accum_no_valid_expense_sheet_ids)

            # 2º) Revisar el resultado de la clasificación
            if not temp_expenses_grouped.empty_to_update_dict():
                # El gasto ha sido reasignado
                # Se comprueba si la hoja a la que ha sido reasignado es válida y si no, se continúa recursivamente
                self.check_expenses_by_month_classification_update(temp_expenses_grouped, temp_reassign_dict)

                # 2.1) Las reasiganciones anidadas no han sido realizadas satisfactoriamente. Seguir recursivamente.
                if temp_reassign_dict:
                    # Se añaden las hojas no válidas anteriores
                    for temp_reassign_values in temp_reassign_dict.values():
                        temp_reassign_values['accum_no_valid_expense_sheet_ids'] += accum_no_valid_expense_sheet_ids
                    # Se llama recursivamente
                    self.reassign_expenses_for_month_classification(temp_reassign_dict, temp_expenses_grouped,
                                                                    expense_classification_method)

                # 2.2) Las reasignaciones anidadas han resultado satisfactorias. Se mergea la lista de to_update
                # con el objeto expenses_grouped "padre"
                if not temp_expenses_grouped.empty_to_update_dict():
                    expenses_grouped.merge_to_update(temp_expenses_grouped)

            # 3º) Se mergean los posibles gastos que van a ser creados del objeto temp
            # en el objeto expenses_grouped "padre"
            if not temp_expenses_grouped.empty_to_create_list():
                expenses_grouped.merge_to_create(temp_expenses_grouped)

            # Elimina objeto temp_expenses_grouped de memoria en cada iteración
            del temp_expenses_grouped


    def expenses_by_monthly_time_method(self, expenses_grouped, expense_classification_method):
        """
        Adds classification by month interval to expenses grouped dict
        :param expenses_grouped: object
        :param expense_classification_method: method to classify expenses
        """
        # TODO problema cuando un gasto llega a este método como para ser incluido en una hoja (to_update)
        #  pero tras la clasificación temporal NO puede ir a esa hoja. ¿Qué ocurre?
        #  a) Se crea en una hoja nueva, a parte
        #       - PROBLEMA: se necesitaría generar la clave para meterlo en los to_create
        #  b) Se busca otra hoja que pueda ya existir en la que se pueda añadir
        #       - PROBLEMA: se necesitaría volver a ejecutar el método de clasificación dinámico
        #                   Y CONTROLANDO que no se seleccione de nuevo la hoja de gastos no válida
        #                   Y, ADEMÁS, puede que no se encuentra a la primera una nueva hoja válida con lo que debería ser un proceso iterativo
        #                   E, incluso,  puede que no se encuentre ninguna, con lo que habría que ir a la opción 'a)'.

        ### UPDATE ###
        # Recorrer los gastos clasificados por to_update e identificar aquellos que no están
        # en una hoja válida según la clasificación temporal
        reassign_dict = {
            # expense_sheet_id: {
            #     'expenses_ids_to_reassign': [expenses ids to reubicate],
            #     'accum_no_valid_expense_sheet_ids': [expense sheet ids no valid for these expenses],
        }
        self.check_expenses_by_month_classification_update(expenses_grouped, reassign_dict)
        ### REASIGNACÍON DE GASTOS to_update ###
        if reassign_dict:
            self.reassign_expenses_for_month_classification(reassign_dict, expenses_grouped,
                                                            expense_classification_method)
        ### FIN UPDATE ###


        ### CREATE ###

        return expenses_grouped

    def check_expenses_by_month_classification_update(self, expenses_grouped, reassign_dict):
        """
        Checks from expenses_grouped to_update list validity for month-year classification
        :param expenses_grouped: object
        :param reassign_dict: dict { expense_sheet_id_no_valid: {
                    'expenses_ids_to_reassign': [expenses ids to reassign],
                    'accum_no_valid_expense_sheet_ids': [no valid expense sheet ids] }
        """
        for expense_sheet_id, expense_ids in expenses_grouped.get_to_update_dict().items():

            # CONDICIÓN 1
            # Comprobar la validez de la hoja para albergar a nuevos gastos clasificando por mes-año
            valid_sheet = self.check_expense_sheet_validity_for_month_classification(expense_sheet_id)

            # CONDICIÓN 2
            if valid_sheet:  # La hoja es válida para la clasificación mes-año. Se comprueban gastos individuales.
                self.check_expenses_validity_for_month_classification(expense_ids, expense_sheet_id, expenses_grouped,
                                                                      reassign_dict)
            else:  # La hoja no es válida. Hay que reassignar todos los gastos relacionados a ella
                expenses_grouped.remove_expenses_from_update_list(expense_sheet_id, expense_ids)
                if expense_sheet_id not in reassign_dict:
                    reassign_dict[expense_sheet_id] = {
                        'expenses_ids_to_reassign': [],
                        'accum_no_valid_expense_sheet_ids': [expense_sheet_id]
                    }
                reassign_dict[expense_sheet_id]['expenses_ids_to_reassign'] += expense_ids

    def check_expense_sheet_validity_for_month_classification(self, expense_sheet_id):
        """
        Checks if expense sheet is valid for expense month-year classification
        :param expense_sheet_id: int
        :return: bool
        """
        valid_sheet = False
        expense_sheet = self.env['hr.expense.sheet'].browse(expense_sheet_id)
        if not expense_sheet.expense_line_ids:
            # Si no tiene gastos, es válida. No tiene un mes-año de referencia aún.
            valid_sheet = True
        elif len(expense_sheet.expense_line_ids) > 1:
            # Si la hoja tiene más de un gasto, se comprueba que todos pertenecen al mismo mes-año
            reference_expense = expense_sheet.expense_line_ids[0]
            if not expense_sheet.mapped('expense_line_ids'). \
                    filtered(lambda exp: exp.date.month != reference_expense.date.month or
                                         exp.date.year != reference_expense.date.year):
                valid_sheet = True  # Todos los gastos pertenecen al mismo mes-año
        else:  # Tiene un gasto, puede albergar nuevos siempre y cuando tengan el mismo mes-año
            reference_expense = expense_sheet.expense_line_ids[0]
            valid_sheet = True
        return valid_sheet

    def check_expenses_validity_for_month_classification(self, expense_ids, expense_sheet_id, expenses_grouped,
                                                         reassign_dict):
        """
        Checks if expenses that don't have the same month-year than one of the expense sheet expenses and
        which of them have to be reassigned to other expense sheet
        :param expense_ids: list of int
        :param expense_sheet_id: int
        :param expenses_grouped: object
        :param reassign_dict: dict { expense_sheet_id_no_valid: {
                    'expenses_ids_to_reassign': [expenses ids to reassign],
                    'accum_no_valid_expense_sheet_ids': [no valid expense sheet ids] }
        :return:
        """
        # Comprobación de cada uno de los gastos que se van a vincular a la hoja
        expense_sheet = self.env['hr.expense.sheet'].browse(expense_sheet_id)
        reference_expense = False

        if expense_sheet.expense_line_ids:  # Se usa un gasto de la hoja como referencia mes-año
            reference_expense = expense_sheet.expense_line_ids[0]
        else:  # Si no tiene gastos, se coge uno de los de la lista
            reference_expense = self.env['hr.expense'].browse(expense_ids[0])

        exp_to_upd_to_reassign = self.env['hr.expense'].browse(expense_ids).filtered(
            lambda exp: exp.date.month != reference_expense.date.month or exp.date.year != reference_expense.date.year)
        if exp_to_upd_to_reassign:

            # Se eliminan los gastos que no pertenecen al mes o año, de la lista de gastos a añadir en la hoja
            expenses_grouped.remove_expenses_from_update_list(expense_sheet_id, exp_to_upd_to_reassign.ids)

            # Se almacenan para reubicar
            if expense_sheet_id not in reassign_dict:
                reassign_dict[expense_sheet_id] = {
                    'expenses_ids_to_reassign': [],
                    'accum_no_valid_expense_sheet_ids': [expense_sheet_id]
                }
            reassign_dict[expense_sheet_id]['expenses_ids_to_reassign'] += exp_to_upd_to_reassign.ids

        return True

    ### Funciones de creación/actualización de hojas de gastos ###

    def analytic_expense_sheet_manage_method(self, expenses_grouped):
        """
        Manages classified expenses for expense sheet creation
        """
        expense_sheet_obj = self.env['hr.expense.sheet']
        # Actualización de hojas de gastos existentes
        for expense_sheet_id, expense_ids in expenses_grouped.get_to_update_dict().items():
            self.env['hr.expense.sheet'].browse(expense_sheet_id).write(
                {'expense_line_ids': [(4, exp_id) for exp_id in expense_ids]})
        # Creación de nuevas hojas de gastos
        for to_create_dict in expenses_grouped.get_to_create_list():
            tuple_key = to_create_dict['classif_key']
            expense_ids = to_create_dict['expense_ids']
            analytic = self.env['account.analytic.account'].browse(tuple_key[0])
            employee_id = tuple_key[1]
            payment_mode = tuple_key[2]
            new_expense_sheet_values = expense_sheet_obj.prepare_expense_sheet_values(employee_id, expense_ids,
                                                                                      payment_mode, analytic)
            expense_sheet_obj.create_expense_sheet_from_analytic_partner(analytic, new_expense_sheet_values)

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
        expenses_grouped = ExpenseGrouping()

        # 1º) Clasificación de gastos en base al método de agrupación indicado
        # Retorna una estructura de datos que el método de gestión de hojas de gasto es capaz de manejar
        expense_classification_method = self.get_expense_sheet_classification_method()

        # Recupera hr.expenses relacionados con los gastos de okticket. Solo aquellos con cuenta anlítica
        hr_expense_ids = [rel.odoo_id.id for rel in self.env['okticket.hr.expense'].search(
            [('id', 'in', okticket_hr_expense_ids)]) if rel.odoo_id.analytic_account_id]
        expenses_grouped = expense_classification_method(expenses_grouped, hr_expense_ids, [])

        # 2º) Reclasificación en base a parámetros temporales
        expense_time_interval_method = self.get_expense_sheet_grouping_time_method()
        expenses_grouped = expense_time_interval_method(expenses_grouped, expense_classification_method)

        # 3º) Creación/actualización de hojas de gasto
        expense_manage_method = self.get_expense_sheet_manage_method()
        expense_manage_method(expenses_grouped)

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

        expense_line_ids = []
        analytic_ids = [(4, analytic.id)]
        for exp in self.env['hr.expense'].browse(expense_ids):
            expense_line_ids.append((4, exp.id))
            if exp.analytic_account_id:
                analytic_ids.append((4, exp.analytic_account_id.id))
                # TODO OJO con este campo por que aquí se vinuclan las account.analytic.account a la hoja pero no sé
                #  si cuando se elimina los gastos se desvinculan...

        return {
            'name': complete_name,
            'employee_id': employee_id,
            'expense_line_ids': expense_line_ids,
            'analytic_ids': analytic_ids,
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
