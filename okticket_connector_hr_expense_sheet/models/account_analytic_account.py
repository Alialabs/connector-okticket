# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    expense_sheet_ids = fields.Many2many('hr.expense.sheet',
                                         'analytic_expense_sheet_rel',
                                         'analytic_id', 'sheet_id')
