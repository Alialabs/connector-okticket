# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class OkticketProductTemplateBinder(Component):
    _name = 'okticket.product.template.binder'
    _inherit = 'okticket.binder'
    _apply_on = ['okticket.product.template']
    _usage = 'binder'
