# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    def _grouping_configuration_dict(self):
        conf_dict = super(HrExpenseBatchImporter, self)._grouping_configuration_dict()
        conf_dict.update({
            'standard': ('standard_classification_method', 'standard_expense_sheet_manage_method'),
        })
        return conf_dict

    def standard_classification_method(self, expense_ids):
        """
        Classifies expenses based on payment mode and employee
        :param expense_ids: list of okticket expense ids
        """
        expenses_grouped_dict = {
            'to_create': {},
            'to_update': {}
        }
        for expense in [rel.odoo_id for rel in self.env['okticket.hr.expense'].search([('id', 'in', expense_ids)])
                        if rel.odoo_id.analytic_account_id]:  # Solo gastos con cuenta analítica

            new_expense_sheet = True
            # Se busca primero entre hojas de gastos con la misma cuenta analítica
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
            # No existen hojas de gastos con la misma cuenta analítica. Se prueba a buscar sin cuenta.
                for expense_sheet in self.env['hr.expense.sheet'].search(
                        [('state', 'in', ['draft']), ('payment_mode', '=', expense.payment_method),
                         ('employee_id', '=', expense.employee_id.id)]):
                    if expense_sheet.id not in expenses_grouped_dict['to_update'].keys():
                        expenses_grouped_dict['to_update'][expense_sheet.id] = []
                    expenses_grouped_dict['to_update'][expense_sheet.id].append(expense.id)
                    new_expense_sheet = False
                    break

            if new_expense_sheet:
                dict_key = (expense.employee_id.id, expense.payment_mode)
                if dict_key not in expenses_grouped_dict['to_create'].keys():
                    expenses_grouped_dict['to_create'][dict_key] = []
                expenses_grouped_dict['to_create'][dict_key].append(expense.id)
        return expenses_grouped_dict

    def standard_expense_sheet_manage_method(self, expenses_grouped_dict):
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
            employee_id = tuple_key[0]
            payment_mode = tuple_key[1]
            analytic = self.env['hr.expense'].browse(expense_ids[0]).analytic_account_id
            new_expense_sheet_values = expense_sheet_obj.prepare_expense_sheet_values(employee_id, expense_ids,
                                                                                      payment_mode, analytic)
            expense_sheet_obj.create_expense_sheet_from_analytic_partner(analytic, new_expense_sheet_values)

    # def expense_sheet_processinga(self, okticket_hr_expense_ids):
    #     """
    #     Grouping expenses based on configuration parameters.
    #     """
    #     return super(HrExpenseBatchImporter, self).expense_sheet_processing(okticket_hr_expense_ids)
    #
    #     # Agrupación tipo 'analytic' por defecto
    #     expense_sheet_grouping_mode = self.backend_record.company_id.expense_sheet_grouping_mode
    #     # Sin división temporal por defecto
    #     expense_sheet_grouping_time = self.backend_record.company_id.expense_sheet_grouping_time
    #
    #     expense_sheet_dict = {}
    #     for expense in [rel.odoo_id for rel in
    #                     self.env['okticket.hr.expense'].search([('id', 'in', okticket_hr_expense_ids),
    #                                                             ('analytic_account_id', '!=', False)])]:
    #         expense_sheets = []
    #
    #         # Búsqueda de posibles hojas de gasto donde vincular el gasto
    #         search_domain = [('state', 'in', ['draft']), ('payment_mode', '=', expense.payment_mode),
    #                          ('employee_id', '=', expense.employee_id.id)]
    #
    #         if expense.analytic_account_id.expense_sheet_ids:
    #             # Si existen hojas de gasto relacionadas con la cuenta analítica del gasto,
    #             # se buscan preferentemente entre estas hojas
    #             # aunque esté configurada una agrupación tipo 'default'.
    #             analytic_search_domain = search_domain + [
    #                 ('id', 'in', expense.analytic_account_id.expense_sheet_ids.ids)]
    #             expense_sheets = self.env['hr.expense.sheet'].search(analytic_search_domain, order='id desc')
    #
    #         if not expense_sheets and expense_sheet_grouping_mode == 'standard':
    #             # En caso de que no haya hojas relacionadas con la cuenta analítica del gasto
    #             # (para elegirlas preferentemente) y la configuración sea tipo 'standar',
    #             # se busca entre las posibles hojas de gasto existentes, dando preferencia a las creadas recientemente
    #             expense_sheets = self.env['hr.expense.sheet'].search(search_domain, order='id desc')
    #
    #         # División temporal de costes solo si es tipo 'monthly'
    #         if expense_sheets and expense_sheet_grouping_time == 'monthly':
    #             new_expense_sheets = []
    #             for exp_sheet in expense_sheets:
    #                 if exp_sheet.mapped('expense_line_ids').filtered(
    #                         lambda exp: exp.date.month == expense.date.month and exp.date.year == expense.date.year):
    #                     new_expense_sheets.append(exp_sheet)
    #             expense_sheets = new_expense_sheets
    #
    #         if expense_sheets:
    #             expense_sheet = expense_sheets[0]
    #             if expense_sheet.id not in expense_sheet_dict:
    #                 expense_sheet_dict[expense_sheet.id] = {
    #                     'expense_list': [],
    #                     'payment_mode': expense.payment_mode,
    #                 }
    #             expense_sheet_dict[expense_sheet.id]['expense_list'].append(expense.id)
    #         else:
    #             self.env['hr.expense.sheet'].create_expense_sheet_from_analytic_partner(
    #                 expense.analytic_account_id,
    #                 expense)
    #
    #     for sheet_id, sheet_values in expense_sheet_dict.items():  # Okticket expense sheet synchronization
    #         exp_list = sheet_values.get('expense_list', [])
    #         sheet_to_updt = self.env['hr.expense.sheet'].browse(sheet_id)
    #         expenses_to_link = [(4, exp_id) for exp_id in exp_list]
    #         sheet_to_updt.write({'expense_line_ids': expenses_to_link, })
