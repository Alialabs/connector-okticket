# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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
