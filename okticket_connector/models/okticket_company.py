# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    okticket_company_id = fields.Integer(string="OkTicket Company_id")
    okticket_import_pending_expenses = fields.Boolean(
        'Import Pending Card Expenses', default=False,
        help='Also import the OkTicket card movements that still have no receipt '
             '(OkTicket status 4). They arrive with no category, so they are given '
             'the default product below, and they are updated with their real '
             'category and receipt once the employee uploads it, as long as the '
             'expense can still be edited in Odoo.')
    okticket_pending_expense_product_id = fields.Many2one(
        'product.product', string='Default Product for Pending Expenses',
        domain=[('can_be_expensed', '=', True)],
        help='Expense category given to the card movements imported with no '
             'receipt. Without it they are skipped, as if the option were off.')
