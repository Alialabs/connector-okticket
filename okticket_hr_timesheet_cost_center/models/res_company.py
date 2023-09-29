# -*- coding: utf-8 -*-
# Copyright 2015-01/10/22 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _create_internal_project_task(self):
        result = super(ResCompany, self.with_context(ignore_okticket_synch=True))._create_internal_project_task()
        return result
