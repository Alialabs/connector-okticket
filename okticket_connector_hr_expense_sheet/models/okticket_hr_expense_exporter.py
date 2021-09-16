# -*- coding: utf-8 -*-
#
#    Created on 2/05/19
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
import logging

_logger = logging.getLogger(__name__)


class HrExpenseExporter(Component):
    _name = 'okticket.hr.expense.exporter'
    _inherit = 'okticket.export.mapper'
    _apply_on = 'okticket.hr.expense'
    _usage = 'hr.expense.exporter'

#TODO : refactorizar con listener y adapter.CRUD (ejemplo a partir de connector_magento_export_partner/models/partner/listener

    # def write_expense(self, expense):

    def set_accounted_expense(self, expense, new_state=True):
        backend_adapter = self.component(usage='backend.adapter')
        if expense:
            # Modiy accounted field
            okticket_expense = self.env['okticket.hr.expense'].search([('odoo_id', '=', expense.id)])
            if okticket_expense:
                vals_dict = {
                    'company_id':  expense.company_id.okticket_company_id,
                    'user_id': expense.employee_id.okticket_user_id,
                    'accounted': new_state,
                }
                backend_adapter.write_expense(okticket_expense.external_id, vals_dict)
        _logger.info('Modify expense accounted field in Okticket !!!')

    def remove_expense(self, expense):
        backend_adapter = self.component(usage='backend.adapter')
        if expense:
            okticket_expense = self.env['okticket.hr.expense'].search([('odoo_id', '=', expense.id)])
            if okticket_expense:
                backend_adapter.remove_expense(okticket_expense.external_id)
        _logger.info('Removed expense in Okticket !!!')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: