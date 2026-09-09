# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Numbered suffixes tried against the API before falling back to a timestamp.
MAX_SHEET_NAME_ATTEMPTS = 20


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

    def apply_free_sheet_name(self, expense_sheet, backend_adapter):
        """Pick a name no report of this company holds, without asking the API.

        The names are read once per run and per backend (a single call for the
        whole company), so the candidate is decided in memory. Posting a name
        just to be told it is taken costs a write attempt and leaves a warning in
        the log for something that is not an incident -- 16 of them in a run over
        a company that already had reports from previous runs.

        Falls through silently when the listing is unavailable: an empty set
        means "unknown", not "nothing is taken", and the caller still has
        ``generate_new_expense_sheet`` to probe the server the old way.

        The numbering matches that fallback exactly, so a sheet gets the same
        name whichever path resolved it.
        """
        taken = backend_adapter.taken_sheet_names()
        base_name = expense_sheet.name
        if not taken or base_name not in taken:
            return base_name

        for index in range(1, MAX_SHEET_NAME_ATTEMPTS + 1):
            candidate = '%s | %s' % (base_name, index)
            if candidate not in taken:
                expense_sheet.write({'name': candidate})
                return candidate

        candidate = '%s-%s' % (base_name, str(datetime.now())[:-7])
        expense_sheet.write({'name': candidate})
        return candidate

    def generate_new_expense_sheet(self, expense_sheet, backend_adapter):
        """
        Generates new expenses sheet with different name for avoiding conflict with any other expense sheet in
        Okticket with a state different from 'draft', a different payment method or a different employee from the
        expense to add.

        Fallback path. ``apply_free_sheet_name`` resolves the name from the
        cached listing before the first attempt, so this now only runs when that
        listing was unavailable, or when the server disagreed with it because a
        report appeared after it was read.

        The name used to be probed with ``backend_adapter.search({'name': ...})``
        before each attempt, up to twenty times. That probe was extremely
        expensive and unreliable at once: ``search`` fetches ``/reports`` with
        ``only_data`` set, so the transport walks *every* page of the whole
        reports collection, and each probe was preceded by a full login. It also
        filtered by name in Python, so the answer depended on what the
        pagination happened to return.

        OkTicket is the authority on report-name uniqueness and says so with a
        422, which ``create`` already turns into a falsy result. So the name is
        simply retried against the server: one call per attempt instead of a
        login plus a full collection scan.
        """
        expense_sheet = self.env['hr.expense.sheet'].browse(expense_sheet.id)
        base_name = expense_sheet.name

        for index in range(1, MAX_SHEET_NAME_ATTEMPTS + 1):
            candidate = '%s | %s' % (base_name, index)
            expense_sheet.write({'name': candidate})
            _logger.info('Creating renamed expense sheet in okticket: %s', candidate)
            res = backend_adapter.create(expense_sheet)
            if res:
                return res

        # Names exhausted: a timestamp cannot collide with an earlier report.
        candidate = '%s-%s' % (base_name, str(datetime.now())[:-7])
        expense_sheet.write({'name': candidate})
        _logger.info('Creating timestamped expense sheet in okticket: %s', candidate)
        res = backend_adapter.create(expense_sheet)
        if not res:
            raise UserError(
                _('It is not possible to find a valid name for the Okticket '
                  'expense sheet "%s" after %s attempts.')
                % (base_name, MAX_SHEET_NAME_ATTEMPTS + 1))
        return res

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
                self.apply_free_sheet_name(expense_sheet, backend_adapter)
                _logger.info(f'Creating in okticket {expense_sheet.name}')
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
            # get_expenses_sheet now returns the flat, fully paginated list. It can
            # still hand back the raw payload when the report holds no expenses,
            # and False when authentication failed, so normalise the three shapes.
            expenses_sheet = backend_adapter.get_expenses_sheet(binding.external_id) or []
            if isinstance(expenses_sheet, dict):
                expenses_sheet = expenses_sheet.get('data') or []
            expenses_external_ids_in_oktk = [expense['_id'] for expense in expenses_sheet
                                             if isinstance(expense, dict) and '_id' in expense]
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
