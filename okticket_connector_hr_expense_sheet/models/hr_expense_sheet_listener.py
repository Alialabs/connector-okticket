# -*- coding: utf-8 -*-
#
#    Created on 31/07/19
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

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if

_logger = logging.getLogger(__name__)


class OkticketHrExpenseSheetBindingExportListener(Component):
    _name = 'okticket.hr.expense.sheet.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['hr.expense.sheet']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        self.export_expense_sheet(record)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        """ Expenses in a expense sheet were modified """
        if fields and 'expense_line_ids' in fields:
            self.export_expense_sheet(record)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_unlink(self, record, fields=None):
        record.delete_expense_sheet()

    def export_expense_sheet(self, record):
        if not record.employee_id.okticket_user_id or \
                record.employee_id.okticket_user_id <= 0:
            _logger.warning(_('Expense employee %s (%s) not related with Okticket user!'),
                            record.employee_id.name,
                            record.employee_id.id)
        else:
            record.export_record()
