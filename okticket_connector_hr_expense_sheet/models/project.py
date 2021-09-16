# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class Project(models.Model):
    _inherit = 'project.project'

    expense_sheet_ids = fields.Many2many('hr.expense.sheet',
                                         'project_expense_sheet_rel',
                                         'project_id', 'sheet_id')
