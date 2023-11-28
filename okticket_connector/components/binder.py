# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import AbstractComponent
from odoo.addons.component.core import Component


class OkticketModelBinder(AbstractComponent):
    _name = 'okticket.binder'
    _inherit = ['base.binder', 'base.okticket.connector']
    _usage = 'binder'


class OkticketExpenseBinder(Component):
    _name = 'okticket.expense.binder'
    _inherit = 'okticket.binder'
    _apply_on = ['okticket.hr.expense']
    _usage = 'binder'
