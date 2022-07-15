# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class HrExpenseListener(Component):
    _name = 'hr.expense.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['hr.expense']

    def on_record_write(self, record, fields=None):
        if 'state' in fields and record['state'] == 'draft':
            record.analytic_account_id.name = record.name
            record.analytic_account_id._okticket_modify_cc_name()
