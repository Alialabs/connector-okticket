# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProjectCostCenter(models.TransientModel):
    """
    This wizard will confirm cost_center creation from projects
    """

    _name = 'project.cost.center.wizard'
    _description = "Confirm cost center creation from project"

    def cost_center_from_project_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        warning_projects = []
        for record in self.env['project.project'].browse(active_ids):
            if record.analytic_account_id and \
                    not record.analytic_account_id.okticket_bind_ids:
                record.analytic_account_id._okticket_create()
            else:
                warning_projects.append(record.name)
        if warning_projects:
            _logger.warning('The next projects have a related cost center or '
                            'not have analytic account: %s', warning_projects)
        return {'type': 'ir.actions.act_window_close'}
