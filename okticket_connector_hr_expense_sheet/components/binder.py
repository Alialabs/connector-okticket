# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class OkticketHrExpenseSheetBinder(Component):
    _name = 'okticket.hr.expense.sheet.binder'
    _inherit = 'okticket.binder'
    _apply_on = ['okticket.hr.expense.sheet']
    _usage = 'binder'
