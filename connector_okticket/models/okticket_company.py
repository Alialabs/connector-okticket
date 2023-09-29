# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    okticket_company_id = fields.Integer(string="OkTicket Company_id")
