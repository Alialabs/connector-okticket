# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

# Values from OkTicket
_payment_method_selection = [('efectivo', 'Cash'), ('tarjeta', 'Business card'),
                             ('cheque', 'Bank check'), ('tarjeta-gas', 'Fuel card'),
                             ('transferencia', 'Transfer'), ('paypal', 'Paypal'), ('na', 'N.A.')]


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    payment_method = fields.Selection(_payment_method_selection, string='Payment method', readonly=True,
                                      copy=False, index=True, track_visibility='onchange', default='na')
    okticket_vat = fields.Char(string='VAT Number')
    okticket_partner_name = fields.Char(string='Partner Name')
    okticket_remote_path = fields.Char(string='Remote Path')
    okticket_remote_uri = fields.Char(string='Remote URI')
    okticket_img = fields.Binary(string='Image')
    okticket_status = fields.Selection([
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='pending')
