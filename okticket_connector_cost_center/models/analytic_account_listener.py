# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class AccountAnalyticCostCenterBindingExportListener(Component):
    _name = 'account.analytic.account.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['project.project']

    def on_record_create(self, record, fields=None):
        record.analytic_account_id._okticket_create()

    def on_record_write(self, record, fields=None):
        if 'name' in fields:
            record.analytic_account_id.name = record.name
            record.analytic_account_id._okticket_modify_cc_name()
