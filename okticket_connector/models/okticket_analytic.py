from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    okticket_cost_center_id = fields.Integer(
        string='OkTicket Cost Center ID',
        default=-1
    )
    okticket_def_account_id = fields.Many2one(
        'account.account',
        string='Default Account for Expenses'
    )

    def get_related_sale_order(self):
        """
        Retrieves the related sale order for the account analytic account.
        :return: sale.order record or False
        """
        self.ensure_one()
        sale_order = self.env['sale.order'].search([
            ('project_account_id', '=', self.id),
            ('state', '=', 'sale')
        ], limit=1)
        return sale_order if sale_order else False
