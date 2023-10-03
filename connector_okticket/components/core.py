# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import AbstractComponent


class BaseOkticketConnectorComponent(AbstractComponent):
    """ Base Okticket Connector Component
    All components of this connector should inherit from it.
    """

    _name = 'base.okticket.connector'
    _inherit = 'base.connector'
    _collection = 'okticket.backend'
