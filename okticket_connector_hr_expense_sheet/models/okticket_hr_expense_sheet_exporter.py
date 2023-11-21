# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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
                    _logger.error('\n\n>>> Deleting error in expense sheet id %s :'
                                  'does not exist in Okticket\n', ok_exp_sheet.external_id)
        _logger.info('Deleted related Expense Sheet in Okticket')

    def run(self, *args):
        """
        Creates new expenses sheet and update expenses that contains
        """
        backend_adapter = self.component(usage='backend.adapter')
        binder = self.component(usage='binder')
        expense_sheet = args and args[0] or False
        # Habilitada la sincronización de hojas en okticket
        if expense_sheet and self.work.collection.okticket_exp_sheet_sync:
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
                link_result = backend_adapter.link_expenses_sheet(binding.external_id, expenses_to_add)
                if not link_result:
                    binding.unlink()  # Delete binding. Some error occurs while linking.
        return True
