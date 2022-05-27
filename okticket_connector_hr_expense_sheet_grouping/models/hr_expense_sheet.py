# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    def expense_sheet_processing(self, okticket_hr_expense_ids):
        """
        Grouping expenses based on configuration parameters.
        """
        # return super(HrExpenseBatchImporter, self).expense_sheet_processing(okticket_hr_expense_ids)

        # Agrupación tipo 'analytic' por defecto
        expense_sheet_grouping_mode = self.backend_record.company_id.expense_sheet_grouping_mode
        # Sin división temporal por defecto
        expense_sheet_grouping_time = self.backend_record.company_id.expense_sheet_grouping_time

        expense_sheet_dict = {}
        for expense in [rel.odoo_id for rel in
                        self.env['okticket.hr.expense'].search([('id', 'in', okticket_hr_expense_ids),
                                                                ('analytic_account_id', '!=', False)])]:
            expense_sheets = []

            # Búsqueda de posibles hojas de gasto donde vincular el gasto
            search_domain = [('state', 'in', ['draft']), ('payment_mode', '=', expense.payment_mode),
                             ('employee_id', '=', expense.employee_id.id)]

            if expense.analytic_account_id.expense_sheet_ids:
                # Si existen hojas de gasto relacionadas con la cuenta analítica del gasto,
                # se buscan preferentemente entre estas hojas
                # aunque esté configurada una agrupación tipo 'default'.
                analytic_search_domain = search_domain + [
                    ('id', 'in', expense.analytic_account_id.expense_sheet_ids.ids)]
                expense_sheets = self.env['hr.expense.sheet'].search(analytic_search_domain, order='id desc')

            if not expense_sheets and expense_sheet_grouping_mode == 'standard':
                # En caso de que no haya hojas relacionadas con la cuenta analítica del gasto
                # (para elegirlas preferentemente) y la configuración sea tipo 'standar',
                # se busca entre las posibles hojas de gasto existentes, dando preferencia a las creadas recientemente
                expense_sheets = self.env['hr.expense.sheet'].search(search_domain, order='id desc')

            # División temporal de costes solo si es tipo 'monthly'
            if expense_sheets and expense_sheet_grouping_time == 'monthly':
                new_expense_sheets = []
                for exp_sheet in expense_sheets:
                    if exp_sheet.mapped('expense_line_ids').filtered(
                            lambda exp: exp.date.month == expense.date.month and exp.date.year == expense.date.year):
                        new_expense_sheets.append(exp_sheet)
                expense_sheets = new_expense_sheets

            if expense_sheets:
                expense_sheet = expense_sheets[0]
                if expense_sheet.id not in expense_sheet_dict:
                    expense_sheet_dict[expense_sheet.id] = {
                        'expense_list': [],
                        'payment_mode': expense.payment_mode,
                    }
                expense_sheet_dict[expense_sheet.id]['expense_list'].append(expense.id)
            else:
                self.env['hr.expense.sheet'].create_expense_sheet_from_analytic_partner(
                    expense.analytic_account_id,
                    expense)

        for sheet_id, sheet_values in expense_sheet_dict.items():  # Okticket expense sheet synchronization
            exp_list = sheet_values.get('expense_list', [])
            sheet_to_updt = self.env['hr.expense.sheet'].browse(sheet_id)
            expenses_to_link = [(4, exp_id) for exp_id in exp_list]
            sheet_to_updt.write({'expense_line_ids': expenses_to_link, })
