# -*- coding: utf-8 -*-
#
#    Created on 8/07/19
#
#    @author:alia
#
#
# 2019 ALIA Technologies
#       http://www.alialabs.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from odoo import _, models, fields, api

import logging
_logger = logging.getLogger(__name__)


class ExpenseWizard(models.TransientModel):
    _name = 'okticket.expense.wizard'

    accounted_state = fields.Boolean('Okticket Accounted State Expense', default=False)

    def set_accounted_state(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids')
        for expense in self.env['hr.expense'].browse(active_ids):
            expense._okticket_accounted_expense(new_state=self.accounted_state)

    @api.multi
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
