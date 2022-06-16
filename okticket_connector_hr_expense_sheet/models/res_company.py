# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    expense_sheet_grouping_method = fields.Selection(
        [('analytic', 'Analytic Account')],
        default='analytic', required=True,
        string='Expense Sheet Grouping Method',
        help=(
            "Expenses grouping method for expense sheets managing:\n"
            "- Analytic Account: expenses group by analytic account, employee and payment mode"
        ),
    )
    expense_sheet_grouping_time = fields.Selection(
        [('no_interval', 'No interval'), ('monthly', 'Monthly')],
        default='no_interval', required=True,
        string='Expense Sheet Grouping Time interval',
        help=(
            "Specify if the expenses must be grouped by time interval."
        ),
    )
