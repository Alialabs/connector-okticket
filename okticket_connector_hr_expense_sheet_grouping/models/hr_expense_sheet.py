# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging
from calendar import monthrange
from datetime import datetime
from odoo.addons.component.core import Component

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    def _grouping_configuration_dict(self):
        conf_dict = super(HrExpenseBatchImporter, self)._grouping_configuration_dict()
        conf_dict.update({
            'standard': 'standard_classification_method',
            'single_expense': 'single_expense_classification_method',
            'no_grouping': 'no_grouping_classification_method',
        })
        return conf_dict

    def _time_grouping_configuration_dict(self):
        conf_dict = super(HrExpenseBatchImporter, self)._time_grouping_configuration_dict()
        conf_dict.update({
            'monthly': 'expenses_by_monthly_time_method',
            'biweekly': 'expenses_by_biweekly_time_method',
        })
        return conf_dict

    ### Funciones de clasificación de gastos ###
    def standard_classification_method(self, expense_ids):
        """
        Classifies expenses based on payment mode and employee
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
            #     'expense_id': expense.id,
            #     'sheet_name': expense.name,
            # }
        ]
        for expense in self.env['hr.expense'].browse(expense_ids):
            grouped_expenses.append({
                'group_fields': {
                    'employee_id': expense.employee_id and expense.employee_id.id,
                    'payment_mode': expense.payment_mode,
                },
                'expense': expense,
                'sheet_name': expense.name,
            })
        return grouped_expenses

    def single_expense_classification_method(self, expense_ids):
        """
        Classifies expenses to create one sheet for each expense
        :param expense_ids: list of okticket expense ids
        :return Grouped expenses structure
        """
        grouped_expenses = []
        for expense in self.env['hr.expense'].browse(expense_ids):
            grouped_expenses.append({
                'group_fields': {
                    'employee_id': expense.employee_id and expense.employee_id.id,
                    'payment_mode': expense.payment_mode,
                    'analytic_ids': expense.analytic_account_id and expense.analytic_account_id.id,
                    'name': expense.okticket_expense_id,  # Campo para generar una hoja por gasto
                },
                'expense': expense,
                'sheet_name': '%s-%s' % (expense.name, expense.employee_id.name),
            })
        return grouped_expenses

    def no_grouping_classification_method(self, expense_ids):
        """
        No grouping
        """
        return []

    ### Funciones de clasificación de gastos por intervalo temporal ###
    def expenses_by_monthly_time_method(self, grouped_expenses):
        """
        Expenses grouped by month (date)
        """
        for expense_data in grouped_expenses:
            expense_date = datetime.strptime(expense_data['expense'].date, '%Y-%m-%d').date()
            month = expense_date.strftime("%B").capitalize()
            expense_data['sheet_name'] = '%s-%s' % (expense_data['sheet_name'], month)
            expense_data['group_fields'].update({
                'init_date': expense_date.replace(day=1),
                'end_date': expense_date.replace(day=monthrange(expense_date.year, expense_date.month)[1]),
            })
        return grouped_expenses

    def expenses_by_biweekly_time_method(self, grouped_expenses):
        """
        Expenses grouped biweekly (date)
        """
        # Indica el día de referencia para dividir el mes
        month_limit_day = self.backend_record.company_id.month_day_limit
        for expense_data in grouped_expenses:
            expense_date = datetime.strptime(expense_data['expense'].date, '%Y-%m-%d').date()
            month = expense_date.strftime("%B").capitalize()

            init_date = expense_date.replace(day=1)
            end_date = expense_date.replace(day=monthrange(expense_date.year, expense_date.month)[1])

            if expense_date.day <= month_limit_day:  # 1ª quincena
                end_date = expense_date.replace(day=month_limit_day)
            else:  # 2ª quincena
                init_date = expense_date.replace(day=month_limit_day)

            expense_data['sheet_name'] = _('%s-%s %s-%s') % \
                                         (expense_data['sheet_name'], month, init_date.day, end_date.day)

            expense_data['group_fields'].update({
                'init_date': init_date,
                'end_date': end_date,
            })

        return grouped_expenses


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    init_date = fields.Date(string="Init Date")
    end_date = fields.Date(string="End Date")

