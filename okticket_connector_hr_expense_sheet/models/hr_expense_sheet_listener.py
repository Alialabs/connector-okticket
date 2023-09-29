# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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
