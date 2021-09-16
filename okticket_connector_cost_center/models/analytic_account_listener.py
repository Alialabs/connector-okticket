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

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class AccountAnalyticCostCenterBindingExportListener(Component):
    _name = 'account.analytic.account.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['project.project']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        record.analytic_account_id._okticket_create()

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if 'name' in fields:
            record.analytic_account_id.name = record.name
            record.analytic_account_id._okticket_modify_cc_name()
        
    # def on_record_unlink(self, record):
    #     print("--- evento unlink escuchado---")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: