# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProjectCostCenter(models.TransientModel):
    """
    This wizard will confirm cost_center creation from projects
    """

    _name = 'project.cost.center.wizard'
    _description = "Confirm cost center creation from project"

    @api.multi
    def cost_center_from_project_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        warning_projects = []
        for record in self.env['project.project'].browse(active_ids):
            if record.analytic_account_id and \
                    not record.analytic_account_id.okticket_bind_ids:
                # tiene cuenta analitica asociada pero no tiene un cost center
                # se crea y asocia uno
                record.analytic_account_id._okticket_create()
            else:
                warning_projects.append(record.name)
        if warning_projects:
            _logger.warning('Los siguientes projectos no tienen cuenta analitica o ya tienen'
                            'un centro de coste asociado: %s', warning_projects)
        return {'type': 'ir.actions.act_window_close'}
