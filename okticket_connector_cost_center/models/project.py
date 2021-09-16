# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Project(models.Model):
    _inherit = 'project.project'

    def _get_cost_center(self):
        for proj in self:
            if proj.analytic_account_id:
                ok_acc_analt = self.env['okticket.account.analytic.account'].search(
                    [('odoo_id', '=', proj.analytic_account_id.id)])
                external_id_int = -1.0
                if ok_acc_analt and ok_acc_analt[0].external_id:
                    external_id_int = int(float(ok_acc_analt[0].external_id))
                proj.okticket_cost_center_id = external_id_int or -1.0

    okticket_cost_center_id = fields.Integer(string="OkTicket Cost_center_id",
                                             default=-1.0,
                                             compute=_get_cost_center,
                                             readonly=True)

    def unlink(self):
        analytic_accounts_to_delete = self.env['account.analytic.account']
        for project in self:
            if project.analytic_account_id and not project.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= project.analytic_account_id
        analytic_accounts_to_delete._okticket_unlink()
        return super(Project, self).unlink()

    def toggle_active(self):
        for project in self:
            if project.analytic_account_id:
                # Modificar estado de project.project
                project.analytic_account_id._okticket_modify_active_state_cost_center(not project.active)
        super(Project, self).toggle_active()

    def unlink_cost_center_from_project(self):
        for record in self:
            record.analytic_account_id.okticket_bind_ids = [(2, ok_bind.id) for ok_bind in
                                                            record.analytic_account_id.okticket_bind_ids]
