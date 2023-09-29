# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    okticket_cost_center_id = fields.Integer(string='OkTicket Cost_center_id', default=-1.0)
    okticket_def_account_id = fields.Many2one('account.account', string='Default Account for Expenses')

    def get_related_sale_order(self):
        """
        Gets account analytic account related sale orders.
        """
        self.ensure_one()
        sale_orders = self.env['sale.order'].search([
            ('analytic_account_id', '=', self.id),
            ('state', '=', 'sale')
        ])
        return sale_orders and sale_orders[0] or False
