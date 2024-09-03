# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging
from calendar import monthrange

from odoo.addons.component.core import Component

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo import _
from babel.dates import format_date

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
            'weekly': 'expenses_by_weekly_time_method',
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
        # for expense in self.env['hr.expense'].browse(expense_ids):
        for expense in self.env['hr.expense'].browse(expense_ids):
            group_fields = {
                'employee_id': expense.employee_id and expense.employee_id.id,
                'payment_mode': expense.payment_mode,
            }
            grouped_expenses.append({
                'group_fields': group_fields,
                'expense': expense,
                'sheet_name': self._get_base_sheet_name(expense, group_fields),
                'suffix': self.build_sheet_name_group_suffix(group_fields)
            })
        return grouped_expenses

    def single_expense_classification_method(self, expense_ids):
        """
        Clasifica gastos para crear una hoja por cada gasto.
        :param expense_ids: lista de ids de gastos de okticket
        :return: Estructura de gastos agrupados
        """
        return [
            self._prepare_grouped_expense(expense, {
                'employee_id': expense.employee_id and expense.employee_id.id,
                'payment_mode': expense.payment_mode,
                #'analytic_ids': expense.analytic_account_id and expense.analytic_account_id.id,
                'name': expense.okticket_expense_id,
            }, suffix=_(" - %s") % expense.name) for expense in self.env['hr.expense'].browse(expense_ids)
        ]

    def no_grouping_classification_method(self, expense_ids):
        """
        Sin agrupación.
        """
        return []

    ### Funciones de clasificación de gastos por intervalo temporal ###
    def expenses_by_monthly_time_method(self, grouped_expenses):
        """
        Agrupa gastos por mes (fecha).
        """
        month_prefix = _("MO")
        for expense_data in grouped_expenses:
            expense_date = expense_data['expense'].date
            month_number = expense_date.strftime("%m")
            year = expense_date.strftime("%Y")
            expense_data['sheet_name'] = f'{month_prefix}{month_number} {year} | {expense_data["sheet_name"]}'
            self._update_group_fields_with_dates(expense_data, expense_date, expense_date.replace(day=1),
                                                 expense_date.replace(day=monthrange(expense_date.year, expense_date.month)[1]))
        return grouped_expenses

    def expenses_by_biweekly_time_method(self, grouped_expenses):
        """
        Agrupa gastos quincenalmente (fecha).
        """
        biweekly_prefix = _("BI")
        month_limit_day = self.backend_record.company_id.month_day_limit
        for expense_data in grouped_expenses:
            expense_date = expense_data['expense'].date
            date_names = self._get_date_names(expense_date)
            init_date, end_date = self._get_biweekly_dates(expense_date, month_limit_day)
            original_sheet_name = self._strip_suffix(expense_data)
            sheet_name = f'{biweekly_prefix} {init_date.day}-{end_date.day} {date_names["month_name"]} {date_names["year"]} | {original_sheet_name}'
            expense_data = self._finalize_sheet_name(expense_data, sheet_name)
            expense_data = self._update_group_fields_with_dates(expense_data, expense_date, init_date, end_date)
        return grouped_expenses

    def expenses_by_weekly_time_method(self, grouped_expenses):
        """
        Agrupa gastos semanalmente (fecha).
        """
        week_prefix = _("WK")
        for expense_data in grouped_expenses:
            expense_date = expense_data['expense'].date
            date_names = self._get_date_names(expense_date)
            init_date = expense_date - timedelta(days=expense_date.weekday())
            end_date = init_date + timedelta(days=6)
            original_sheet_name = self._strip_suffix(expense_data)
            sheet_name = f'{week_prefix}{date_names["week"]} {date_names["year"]} | {original_sheet_name}'
            self._finalize_sheet_name(expense_data, sheet_name)
            self._update_group_fields_with_dates(expense_data, expense_date, init_date, end_date)
        return grouped_expenses

    ### Métodos de utilidad ###
    def _prepare_grouped_expense(self, expense, group_fields, suffix=None):
        return {
            'group_fields': group_fields,
            'expense': expense,
            'sheet_name': self._get_base_sheet_name(expense, group_fields),
            'suffix': suffix or self.build_sheet_name_group_suffix(group_fields)
        }

    def _update_group_fields_with_dates(self, expense_data, expense_date, init_date, end_date):
        expense_data['group_fields'].update({
            'init_date': init_date,
            'end_date': end_date,
        })
        return expense_data

    def _get_date_names(self, date):
        user_lang = self.env.user.lang or 'en_US'  # Obtén el idioma del usuario
        month_name = format_date(date, "MMMM", locale=user_lang)  # Obtén el nombre del mes traducido
        return {
            'month_name': month_name.capitalize(),
            'month_number': date.strftime("%m"),
            'year': date.strftime("%Y"),
            'year_short': date.strftime("%y"),
            'week': date.strftime("%V"),
        }

    def _get_biweekly_dates(self, expense_date, month_limit_day):
        if expense_date.day <= month_limit_day:  # 1ª quincena
            return expense_date.replace(day=1), expense_date.replace(day=month_limit_day)
        else:  # 2ª quincena
            return expense_date.replace(day=month_limit_day + 1), expense_date.replace(day=monthrange(expense_date.year, expense_date.month)[1])

    def _strip_suffix(self, expense_data):
        original_sheet_name = expense_data['sheet_name']
        if 'suffix' in expense_data:
            original_sheet_name = original_sheet_name.replace(expense_data['suffix'], '')
        return original_sheet_name

    def _finalize_sheet_name(self, expense_data, sheet_name):
        if 'suffix' in expense_data:
            sheet_name += expense_data['suffix']
        expense_data['sheet_name'] = sheet_name
        return expense_data


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    init_date = fields.Date(string="Init Date")
    end_date = fields.Date(string="End Date")
