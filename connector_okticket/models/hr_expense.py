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

    is_invoice = fields.Boolean(string='Is invoice',
                                default=False)
    okticket_deleted = fields.Boolean(string='Deleted in Okticket',
                                      default=False)

    @api.depends('sheet_id', 'sheet_id.account_move_id', 'sheet_id.state')
    def _compute_state(self):
        """
        Checks if expense is in draft state and has okticket_deleted = True.
        If true, removes expense.
        """
        super(HrExpense, self)._compute_state()
        expenses_to_unlink = self.filtered(lambda exp: exp.okticket_deleted and exp.state == 'draft')
        if expenses_to_unlink:
            expenses_to_unlink.unlink()

    @api.multi
    def unlink(self):
        for expense in self:
            if expense.state not in ['draft']:
                raise UserError(_('Delete expenses in a state different from draft is not allowed.'))
        if self:
            self.registry_expense_unlink_op()
        return super(HrExpense, self).unlink()

    def registry_expense_unlink_op(self):
        """
        Generates log.event message to registry expense unlink
        """
        msg = 'User %s [ID: %s] has deleted the following expenses: ' % (self.env.user.name, self.env.uid)
        msg += " | ".join(['ID: %s - OKTICKET_ID: %s' % (exp.id, exp.okticket_expense_id) for exp in self])
        self.env['log.event'].add_event({
            'backend_id': False,
            'msg': msg,
        })
