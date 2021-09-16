# -*- coding: utf-8 -*-
#
#    Created on 4/07/19
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


from odoo.addons.component.core import Component
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    def check_selected_expense_sheet(self, proj_expense_sheet, expense, expense_sheet_dict):
        '''
        Comprueba si la hoja de gastos es válida para aceptar el nuevo gasto.
        Debe estar en estado borrador, tener el mismo modo de pago y pertenecer al mismo empleado
        '''
        if proj_expense_sheet.state in ['draft'] and \
                (not proj_expense_sheet.payment_mode or \
                expense.payment_mode == proj_expense_sheet.payment_mode) and \
                expense.employee_id.id == proj_expense_sheet.employee_id.id and \
                (not proj_expense_sheet.id in expense_sheet_dict or \
                expense_sheet_dict[proj_expense_sheet.id]['payment_mode'] == expense.payment_mode):
            # Inicializa diccionario de hojas de gasto
            if not proj_expense_sheet.id in expense_sheet_dict:
                expense_sheet_dict[proj_expense_sheet.id] = {
                    'expense_list': [],
                    'payment_mode': expense.payment_mode,
                }
            expense_sheet_dict[proj_expense_sheet.id]['expense_list'].append(expense.id)
            return True
        return False

    def run(self, filters=None, options=None):
        okticket_hr_expense_ids = super(HrExpenseBatchImporter, self).run(filters=filters, options=options)
        expense_sheet_dict = {}
        for expense in [rel.odoo_id for rel in self.env['okticket.hr.expense'].search([('id', 'in', okticket_hr_expense_ids)])]:
            if expense.analytic_account_id:
                expense_sheet = False
                project = self.env['project.project'].search([('analytic_account_id', '=', expense.analytic_account_id.id)],limit=1)
                for proj_expense_sheet in project.expense_sheet_ids:
                    # Hoja de cálculo según estado, modo de pago y empleado
                    if self.check_selected_expense_sheet(proj_expense_sheet, expense, expense_sheet_dict):
                        expense_sheet = proj_expense_sheet
                        break
                if not expense_sheet:
                    self.env['hr.expense.sheet'].create_expense_sheet_from_project_partner(project, expense)
        # OPTIMIZACION
        for sheet_id, sheet_values in expense_sheet_dict.items(): # Actualización de hojas de gastos en Okticket
            exp_list = sheet_values.get('expense_list',[])
            sheet_to_updt = self.env['hr.expense.sheet'].browse(sheet_id)
            expenses_to_link = [(4, exp_id) for exp_id in exp_list]
            sheet_to_updt.write({'expense_line_ids': expenses_to_link, })
        return okticket_hr_expense_ids


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    project_ids = fields.Many2many('project.project',
                                    'project_expense_sheet_rel',
                                    'sheet_id', 'project_id')

    def create_expense_sheet_from_project_partner(self, project, expense):
        '''
        Creates new hr.expense.sheet from project and expense data
        :param project: browse project.project
        :param expense: browse hr.expense
        :return: new hr.expense.sheet
        '''
        _logger.debug("Account ID: " + expense.analytic_account_id.name + " - Expense ID: " + str(expense.id) + " - Expense OkTicket-ID: " + expense.okticket_expense_id)
        new_expense_sheet = False
        if project and expense:
            sale_order_client = project and project.sale_order_id and project.sale_order_id.partner_id \
                                and project.sale_order_id.partner_id.name or 'NO CLIENT'
            project_name = project and project.name or 'NO PROJECT'
            complete_name = '-'.join([sale_order_client, project_name])
            sale_order = project and project.sale_order_id and project.sale_order_id or False
            sheet_vals = {
                'name': complete_name,
                'employee_id': expense.employee_id and expense.employee_id.id or False,
                'expense_line_ids': [(4, expense.id)],
                'project_ids': [(4, project.id)],
                'user_id': sale_order and sale_order.user_id and sale_order.user_id.id
                           or False, # Responsable
                'payment_mode': expense.payment_mode,
            }
            new_expense_sheet = self.create(sheet_vals)
        else:
            _logger.error("Error in expense sheet create process")
            msg = "Error in expense sheet create process" + \
                           "Account ID: " + expense.analytic_account_id.name + " - Expense ID: " + \
                           str(expense.id) + " - Expense OkTicket-ID: " + expense.okticket_expense_id
            event = {
                'backend_id': self.env['okticket.backend'].search([('active', '=', True)], limit=1).id,
                'type': 'error',
                'tag': 'OP',
                'msg': msg,
            }
            self.env['log.event'].add_event(event)
        return new_expense_sheet


    @api.multi
    def action_submit_sheet(self):
        '''
        "Enviar al responsable"
        Implica:
            - Setear el atributo 'accounted' = 'true' en los gastos contenidos en la hoja en Okticket.
            - Action [347] Okticket
        '''
        super(HrExpenseSheet, self).action_submit_sheet()
        for expense in self.expense_line_ids:
            expense._okticket_accounted_expense(new_state=True) # 'accounted': 'True'
        # TODO gestión más eficiente de id de status_id de hojas de gasto de Okticket
        action_id = 347
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    @api.multi
    def reset_expense_sheets(self):
        '''
        Desde estado "Enviada" y "Rechazada": "Cambiar a borrador"/"Reabrir(Empleado)"
        Implica:
            - Setear el atributo 'accounted' = 'false' en los gastos contenidos en la hoja en Okticket.
            - Action [348] Okticket desde estado "Enviada"
            - Action [354] Okticket desde estado "Rechazada"
        '''
        if self.state == 'cancel':
            action_id = 354  # Desde "Rechazada"
        else:
            action_id = 348  # Desde "Enviada"
        if super(HrExpenseSheet, self).reset_expense_sheets():
            for expense in self.expense_line_ids:
                expense._okticket_accounted_expense(new_state=False)
            self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    @api.multi
    def refuse_sheet(self, reason):
        '''
        Desde estado "Enviada" y "Aprobada": "Rechazar"/"Rechazar(Admin)"
        Implica:
            - Setear el atributo 'accounted' = 'false' en los gastos contenidos en la hoja en Okticket.
            - Action [350] Okticket desde estado "Enviada"
            - Action [352] Okticket desde estado "Aprobada"
        '''
        if self.state == 'approve':
            action_id = 352  # Desde "Aprobada"
        else:
            action_id = 350  # Desde "Enviada"
        super(HrExpenseSheet, self).refuse_sheet(reason)
        for expense in self.expense_line_ids:
            expense._okticket_accounted_expense(new_state=False)
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id, comments=reason)

    @api.multi
    def approve_expense_sheets(self):
        '''
        "Aprobar"/"Aprobar(Admin)"
        Implica:
            - Action [349] Okticket
        '''
        super(HrExpenseSheet, self).approve_expense_sheets()
        # Se incluye el producto "gasto" como una sale.order.line del sale.order vinculado al hr.expense
        # self.expense_line_ids.add_as_sale_order_lines()

        # for expense in self.expense_line_ids:
        #     expense._okticket_remove_expense()
        action_id = 349
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    @api.multi
    def action_sheet_move_create(self):
        '''
        "Publicar asientos"/"Publicar asientos(Admin)"
        Implica:
            - Action [351] Okticket
        '''
        res = super(HrExpenseSheet, self).action_sheet_move_create()
        if res:
            action_id = 351
            self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)
        return res

    @api.multi
    def action_sheet_payment_registry(self, body):
        '''
        "Registrar pago"/"Registrar pago(Admin)"
        Implica:
            - Action [353] Okticket
        '''
        action_id = 353
        self.env['okticket.hr.expense.sheet'].change_expense_sheet_status(self, action_id)

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, body='', **kwargs):
        result = super(HrExpenseSheet, self).message_post(body=body, **kwargs)
        if result and self.env.context and self.env.context.get('okticket_synch'):
            self.action_sheet_payment_registry(body)
        return result


    @api.multi
    def unlink(self):
        return super(HrExpenseSheet, self).unlink()


class HrExpenseSheetRegisterPaymentWizard(models.TransientModel):
    _inherit = 'hr.expense.sheet.register.payment.wizard'

    @api.multi
    def expense_post_payment(self):
        super(HrExpenseSheetRegisterPaymentWizard, self.with_context(
            okticket_synch=True,
        )).expense_post_payment()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: