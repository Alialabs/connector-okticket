# -*- coding: utf-8 -*-
#
#    Created on 09/06/22
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
from datetime import datetime

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrExpenseExporter(Component):
    _inherit = 'okticket.hr.expense.sheet.exporter'

    def delete_expense_sheet(self, exp_sheet):
        """
        Run the synchronization for all users, using the connector crons.
        """
        backend_adapter = self.component(usage='backend.adapter')
        if exp_sheet:
            # Eliminar expense.sheet
            okticket_exp_sheet_ids = [okticket_exp_sheet.id for okticket_exp_sheet in exp_sheet]
            for ok_exp_sheet in self.env['okticket.hr.expense.sheet'].search(
                    [('odoo_id', 'in', okticket_exp_sheet_ids)]):
                try:
                    backend_adapter.delete_expense_sheet(ok_exp_sheet.external_id)
                except Exception as e:
                    _logger.error('\n\n    >>> ERROR ELIMINACION EXP SHEET ID: %s no localizacdo en OKTICKET\n',
                                  ok_exp_sheet.external_id)
        _logger.info('Deleted related Expense Sheet in Okticket !!!')
