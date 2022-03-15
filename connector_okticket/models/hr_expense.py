# -*- coding: utf-8 -*-
#
#    Created on 16/04/19
#
#    @author:alia
#
#
# 2019 ALIA Technologies
#       http://www.alialabs.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from odoo import fields, models, api, _
from odoo.exceptions import UserError

_payment_method_selection = [('efectivo', 'Efectivo'), ('tarjeta', 'Tarjeta empresa'),
                             ('cheque', 'Cheque bancario'), ('tarjeta-gas', 'Tarjeta combustible'),
                             ('transferencia', 'Transferencia'), ('paypal', 'Paypal'), ('na', 'N.A.')]


# def get_payment_methods():
#     return [ tuple_sel[0] for tuple_sel in _payment_method_selection ]


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

    is_invoice = fields.Boolean(string='Is invoice', default=False)

    @api.multi
    def unlink(self):
        for expense in self:
            if expense.state in ['reported']:
                raise UserError(_('You cannot delete a reported expense.'))
        return super(HrExpense, self).unlink()
