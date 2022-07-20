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
from datetime import datetime

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class HrExpenseSheetMapper(Component):
    _name = 'okticket.expense.sheet.mapper'
    _inherit = 'okticket.import.mapper'
    _apply_on = 'okticket.hr.expense.sheet'
    _usage = 'mapper'

    @mapping
    def external_id(self, record):
        return {'external_id': record['_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


class HrExpenseExporter(Component):
    _name = 'okticket.hr.expense.sheet.exporter'
    _inherit = 'okticket.export.mapper'
    _apply_on = 'okticket.hr.expense.sheet'
    _usage = 'record.exporter'

    def generate_new_expense_sheet(self, expense_sheet, backend_adapter):
        """
        Generates new expenses sheet with different name for avoiding conflict with any other expense sheet in
        Okticket with a state different from 'draft', a different payment method or a different employee from the
        expense to add.
        """
        index = 0
        date_now = datetime.now()
        date_str = str(date_now)[:-7]
        new_name_to_test = expense_sheet.name + '-' + date_str
        new_name_to_test = new_name_to_test.replace(" ", "_")
        found_exp_sheets = True
        max_tries = 20  # Tries search a valid name until 20 times
        while found_exp_sheets:
            found_exp_sheets = backend_adapter.search({'name': new_name_to_test})
            if found_exp_sheets:
                new_name_to_test = new_name_to_test + '-' + str(index)
                index += 1
            max_tries -= 1
            if max_tries == 0:
                raise Exception(_("(generate_new_expense_sheet): It is not possible to find a valid name for "
                                  "expenses sheet: %s"), expense_sheet.name)
        expense_sheet = self.env['hr.expense.sheet'].browse(expense_sheet.id)
        expense_sheet.write({'name': new_name_to_test})
        return backend_adapter.create(expense_sheet)

    def run(self, *args):
        """
        Creates new expenses sheet and update expenses that contains
        """
        backend_adapter = self.component(usage='backend.adapter')
        binder = self.component(usage='binder')
        expense_sheet = args and args[0] or False
        if expense_sheet:
            binding = expense_sheet.okticket_bind_ids and \
                      expense_sheet.okticket_bind_ids[0] or False
            if not binding:
                creation_result = backend_adapter.create(expense_sheet)
                if not creation_result:
                    # New expenses sheet
                    creation_result = self.generate_new_expense_sheet(expense_sheet, backend_adapter)
                mapper = self.component(usage='mapper')
                external_data = creation_result['data']
                internal_data = mapper.map_record(external_data).values()
                internal_data.update({'odoo_id': expense_sheet.id, })
                binding = self.model.create(internal_data)
                binder.bind(internal_data['external_id'], binding)
                _logger.info('Created and synchronized expense sheet')
            # Exists binding. Okticket expenses sheet will be updated.
            expenses_sheet = backend_adapter.get_expenses_sheet(binding.external_id).get('data', [])
            expenses_external_ids_in_oktk = [expense['_id'] for expense in expenses_sheet if '_id' in expense]
            expenses_to_add = []
            for expense in expense_sheet.expense_line_ids:
                if expense.okticket_bind_ids:
                    if not expense.okticket_bind_ids[0].external_id in expenses_external_ids_in_oktk:
                        expenses_to_add.append(expense)
                    else:
                        expenses_external_ids_in_oktk.remove(expense.okticket_bind_ids[0].external_id)
            if expenses_external_ids_in_oktk:
                # Expenses that don't exist in Odoo but exists in a Okticket expenses sheet should be deleted
                # This case shouldn't occur. It would implied management operations from Okticket
                backend_adapter.unlink_expenses_sheet(expenses_external_ids_in_oktk)
            if expenses_to_add:
                # Add expenses from Odoo expenses sheet to Okticket expenses sheet
                backend_adapter.link_expenses_sheet(binding.external_id, expenses_to_add)
        return True
