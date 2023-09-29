# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import AbstractComponent


class OkticketImportMapper(AbstractComponent):
    _name = 'okticket.import.mapper'
    _inherit = ['base.okticket.connector', 'base.import.mapper']
    _usage = 'import.mapper'


class OkticketExportMapper(AbstractComponent):
    _name = 'okticket.export.mapper'
    _inherit = ['base.okticket.connector', 'base.export.mapper']
    _usage = 'export.mapper'
