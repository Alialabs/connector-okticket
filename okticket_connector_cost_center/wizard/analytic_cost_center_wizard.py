# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountAnalyticAccountCostCenter(models.TransientModel):
    """
    This wizard will confirm cost_center creation from analytic accounts
    """

    _name = 'analytic.cost.center.wizard'
    _description = "Confirm cost center creation from analytic account"

    def cost_center_from_analytic_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        warning_analytic = []
        for record in self.env['account.analytic.account'].browse(active_ids):
            if not record.okticket_bind_ids:
                record._okticket_create()
            else:
                warning_analytic.append(record.name)
        if warning_analytic:
            _logger.warning('The next analytic accounts have a related cost center: %s',
                            warning_analytic)
        return {'type': 'ir.actions.act_window_close'}
