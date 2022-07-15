# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class HREXpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def action_sheet_move_create(self):
        for record_id in self:
            splitall = True
            split = False
            # if len(
            #         record_id.expense_line_ids.filtered(
            #             lambda x: x.payment_mode != 'company_account')):
            #     splitall = True
            for e in record_id.expense_line_ids:
                # if e.payment_mode != 'company_account':
                #     continue
                if len(record_id.expense_line_ids) < 2:
                    continue
                if split or splitall:
                    self.env["hr.expense.sheet"].create({
                        # 'expense_line_ids':
                        # [(4,record_id,
                        "employee_id":
                            e.employee_id.id if e.employee_id else False,
                        "payment_mode":
                            "company_account",
                        "name": e.name,
                        "accounting_date":
                            e.date,
                        "expense_line_ids": [(4, e.id, 0)]
                    })
                else:
                    split = True
                    record_id.accounting_date = e.date
                # if e.invoice_id:
                #     e.invoice_id.action_invoice_open(
                #         skip_expense_procesing=True)
                if e.sheet_id != record_id:
                    e.sheet_id.action_submit_sheet()
                    e.sheet_id.approve_expense_sheets()
                    super(HREXpenseSheet,
                          e.sheet_id).action_sheet_move_create()

        return super().action_sheet_move_create()
