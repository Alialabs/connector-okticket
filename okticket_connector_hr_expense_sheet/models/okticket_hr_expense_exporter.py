# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import _
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrExpenseExporter(Component):
    _name = 'okticket.hr.expense.exporter'
    _inherit = 'okticket.export.mapper'
    _apply_on = 'okticket.hr.expense'
    _usage = 'hr.expense.exporter'

    def set_accounted_expense(self, expense, new_state=True):
        backend_adapter = self.component(usage='backend.adapter')
        if expense:
            okticket_expense = self.env['okticket.hr.expense'].search([('odoo_id', '=', expense.id)])
            if okticket_expense:
                vals_dict = {
                    'company_id': expense.company_id.okticket_company_id,
                    'user_id': expense.employee_id.okticket_user_id,
                    'accounted': new_state,
                }
                backend_adapter.write_expense(okticket_expense.external_id, vals_dict)
        _logger.info(_('Modify expense accounted field in Okticket'))

    # def remove_expense(self, expense):
    #     backend_adapter = self.component(usage='backend.adapter')
    #     if expense:
    #         okticket_expense = self.env['okticket.hr.expense'].search([('odoo_id', '=', expense.id)])
    #         if okticket_expense:
    #             backend_adapter.remove_expense(okticket_expense.external_id)
    #     _logger.info(_('Removed expense in Okticket'))
