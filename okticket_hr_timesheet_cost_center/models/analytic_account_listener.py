# -*- coding: utf-8 -*-
# Copyright 2015-01/10/22 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class AccountAnalyticCostCenterBindingExportListener(Component):
    _inherit = 'account.analytic.account.binding.export.listener'

    def on_record_create(self, record, fields=None):
        if 'ignore_okticket_synch' not in self.env.context or not self.env.context['ignore_okticket_synch']:
            super(AccountAnalyticCostCenterBindingExportListener, self).on_record_create(record, fields=fields)
