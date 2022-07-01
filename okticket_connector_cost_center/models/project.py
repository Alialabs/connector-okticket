# -*- coding: utf-8 -*-
#
#    Created on 5/07/19
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

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Project(models.Model):
    _inherit = 'project.project'

    # def _get_cost_center(self):
    #     for proj in self:
    #         if proj.analytic_account_id:
    #             ok_acc_analt = self.env['okticket.account.analytic.account'].search(
    #                 [('odoo_id', '=', proj.analytic_account_id.id)])
    #             external_id_int = -1.0
    #             if ok_acc_analt and ok_acc_analt[0].external_id:
    #                 external_id_int = int(float(ok_acc_analt[0].external_id))
    #             proj.okticket_cost_center_id = external_id_int or -1.0
    #
    # okticket_cost_center_id = fields.Integer(string="OkTicket Cost_center_id",
    #                                          default=-1.0,
    #                                          compute=_get_cost_center,
    #                                          readonly=True)

    def unlink(self):
        analytic_accounts_to_delete = self.env['account.analytic.account']
        for project in self:
            if project.analytic_account_id and not project.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= project.analytic_account_id
        analytic_accounts_to_delete._okticket_unlink()
        return super(Project, self).unlink()

    @api.multi
    def toggle_active(self):
        for project in self:
            if project.analytic_account_id:
                # Modificar estado de project.project
                project.analytic_account_id._okticket_modify_active_state_cost_center(not project.active)
        super(Project, self).toggle_active()
