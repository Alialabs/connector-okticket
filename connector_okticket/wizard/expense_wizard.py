# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, models, fields

_logger = logging.getLogger(__name__)


class ExpenseWizard(models.TransientModel):
    _name = 'okticket.expense.wizard'

    accounted_state = fields.Boolean('Okticket Accounted State Expense', default=False)

    def set_accounted_state(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids')
        for expense in self.env['hr.expense'].browse(active_ids):
            expense._okticket_accounted_expense(new_state=self.accounted_state)

    def assign_default_expense_account(self):
        info_msg_refs = []
        for expense in self.env['hr.expense'].browse(self.env.context.get('active_ids')):
            expense.account_id = expense.product_id and expense.product_id.property_account_expense_id \
                                 and expense.product_id.property_account_expense_id.id \
                                 or expense.account_id and expense.account_id.id \
                                 or False
            info_msg_refs.append(expense.name)
        _logger.info(_('(assign_default_expense_account)> Field "account_id" updated from product for expenses: %s'),
                     ', '.join(info_msg_refs))
