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
        selection_add=[('standard', 'Standard')], default='standard',
        ondelete={
            'standard': 'set analytic',
        },
        help=(
            "Expenses grouping method for expense sheets managing:\n"
            "- Analytic Account: expenses group by analytic account, employee and payment mode"
            "- Standard: expenses grouped by employee and payment mode (Odoo standard)"
        ),
    )
