from odoo import fields, models, api, _
from odoo.exceptions import UserError

# Values from OkTicket
_payment_method_selection = [('efectivo', 'Cash'), ('tarjeta', 'Business card'),
                             ('cheque', 'Bank check'), ('tarjeta-gas', 'Fuel card'),
                             ('transferencia', 'Transfer'), ('paypal', 'Paypal'), ('na', 'N.A.')]


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    payment_method = fields.Selection(_payment_method_selection,
                                      string='Payment method', readonly=True,
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

    okticket_response = fields.Text(string='Okticket Response')

    analytic_account_id = fields.Many2one(
        string="Analytic account from OkTicket",
        comodel_name="account.analytic.account",
        store=True,
        help="Cost center (analytical account) from OkTicket synchronization",
    )

    @api.depends('sheet_id', 'sheet_id.account_move_ids', 'sheet_id.state')
    def _compute_state(self):
        """
        Checks if the expense is in draft state and has okticket_deleted = True.
        If true, removes the expense.
        """
        super(HrExpense, self)._compute_state()
        self._remove_deleted_draft_expenses()

    def _remove_deleted_draft_expenses(self):
        expenses_to_unlink = self.filtered(lambda exp: exp.okticket_deleted and exp.state == 'draft')
        if expenses_to_unlink:
            expenses_to_unlink.unlink()

    def unlink(self):
        self._check_unlink_conditions()
        self._log_expense_unlink_op()
        return super(HrExpense, self).unlink()

    def _check_unlink_conditions(self):
        for expense in self:
            if expense.state != 'draft':
                raise UserError(_('Deleting expenses in a state different from draft is not allowed.'))

    def _log_expense_unlink_op(self):
        if self:
            msg = self._generate_unlink_log_message()
            self.env['log.event'].add_event({
                'backend_id': False,
                'msg': msg,
            })

    def _generate_unlink_log_message(self):
        user_info = 'User %s [ID: %s]' % (self.env.user.name, self.env.uid)
        expense_info = " | ".join(['ID: %s - OKTICKET_ID: %s' % (exp.id, exp.okticket_expense_id) for exp in self])
        return f'{user_info} has deleted the following expenses: {expense_info}'
