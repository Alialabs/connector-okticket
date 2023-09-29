# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class OkticketAccountAnalyticAccountBinder(Component):
    _name = 'okticket.account.analytic.account.binder'
    _inherit = 'okticket.binder'
    _apply_on = ['okticket.account.analytic.account']
    _usage = 'account.analytic.account.binder'
