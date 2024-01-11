# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    expense_sheet_grouping_method = fields.Selection(
        selection_add=[('standard', 'Standard'),
                       ('single_expense', 'Single expense sheet'),
                       ('no_grouping', 'No grouping')],
        default='no_grouping',
        # ondelete={
        #     'standard': 'set analytic',
        #     'single_expense': 'set analytic',
        #     'no_grouping': 'set analytic',
        # },
        help=(
            "Expenses grouping method for expense sheets managing:\n"
            "- Analytic Account: expenses group by analytic account, employee and payment mode"
            "- Standard: expenses grouped by employee and payment mode (Odoo standard)"
        ),
    )
    expense_sheet_grouping_time = fields.Selection(
        selection_add=[('monthly', 'Monthly'), ('biweekly', 'Biweekly')],
        # ondelete={
        #     'monthly': 'set no_interval',
        # }
    )
    sheet_name_format = fields.Char(string='Sheet Name Format', default='{name} - {m}/{y} - {init_date}-{end_date}',
                                    help=(
                                        "{name} - Sheet Name\n"
                                        "{M} - Full month name. January, February, ...\n"
                                        "{m} - Month as a zero-padded decimal number. 01, 02, ..., 12\n"
                                        "{Y} - Year with century as a decimal number. 2013, 2019\n"
                                        "{y} - Year without century as a zero-padded decimal number. 00, 01, ..., 99\n"
                                        "{id} - First day as number. 1, 2, ..., 31\n"
                                        "{ed} - Last day as number. 1, 2, ..., 31\n"
                                    ))
    month_day_limit = fields.Integer(
        string='Month day',
        default=15)
