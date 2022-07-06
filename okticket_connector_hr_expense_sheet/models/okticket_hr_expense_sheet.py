# -*- coding: utf-8 -*-
#
#    Created on 31/07/19
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

import logging

from odoo import _, api, fields, models
from odoo.addons.component.core import Component
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.expense.sheet',
        inverse_name='odoo_id',
        string='Hr Expense Sheet Bindings', )

    def _get_expense_sheet(self):
        for exp_sheet in self:
            external_ids = [ok_exp_sheet.external_id for ok_exp_sheet in exp_sheet.okticket_bind_ids]
            exp_sheet.okticket_expense_sheet_id = external_ids and external_ids[0] or '-1'

    okticket_expense_sheet_id = fields.Char(string="OkTicket Expense_sheet_id",
                                            default='-1',
                                            compute=_get_expense_sheet,
                                            readonly=True)

    @api.multi
    def export_record(self, *args, **kwargs):
        """ Creates a new expense sheet on Okticket """
        self.env['okticket.hr.expense.sheet'].sudo().export_record(self)
        return True


class OkticketHrExpenseSheet(models.Model):
    _name = 'okticket.hr.expense.sheet'
    _inherit = 'okticket.binding'
    _inherits = {'hr.expense.sheet': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='hr.expense.sheet',
        string='Hr Expense Sheet',
        required=True,
        ondelete='cascade',
    )

    @api.model
    def export_expense_sheet(self, backend=False, filters=None, **kwargs):
        backend = backend or self.env['okticket.backend'].get_default_backend_okticket_connector()
        backend.ensure_one()
        with backend.work_on(self._name) as work:
            importer = work.component(usage='importer')
            try:
                importer.run(filters=filters)
            except Exception as e:
                _logger.error('Exception: %s\n', e)
                import traceback
                traceback.print_exc()
                raise UserError(_('Could not connect to Okticket'))

    @api.multi
    def change_expense_sheet_status(self, expense_sheets, action_id, comments='No comment'):
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        backend.ensure_one()
        with backend.work_on(self._name) as work:
            adapter = work.component(usage='backend.adapter')
            try:
                return adapter.change_expense_sheet_status(expense_sheets, action_id, comments=comments)
            except Exception as e:
                _logger.error('Exception: %s\n', e)
                import traceback
                traceback.print_exc()
                raise UserError(_('Could not connect to Okticket'))


class HrExpenseSheetAdapter(Component):
    _name = 'okticket.hr.expense.sheet.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.hr.expense.sheet'

    def prepare_values(self, values):
        """
        Generates prepares valid values dictionary to create a expense sheet in Okticket from other one
        :param values: values dict
        :return: prepared values dict
        """
        return {
            'name': values.name,
            'user_id': values.employee_id.okticket_user_id,
            'company_id': values.company_id.okticket_company_id,
        }

    def create(self, values):
        if self._auth():
            result = self.create_expense_sheet(self.prepare_values(values))
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de create
    def create_expense_sheet(self, values):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/reports')
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json', }
        return okticketapi.general_request(url, "POST", fields_dict=values,
                                           headers=header, only_data=False, https=self.collection.https)

    def get_expenses_sheet(self, external_id):
        if self._auth():
            result = self.get_expenses_sheet_api(external_id)  # para la api
            # Log event
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return False

    # TODO : en api
    def get_expenses_sheet_api(self, external_id):
        okticketapi = self.okticket_api
        path = '/reports/%s/expenses' % external_id
        url = okticketapi.get_full_path(path)
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json', }
        return okticketapi.general_request(url, "GET", fields_dict={},
                                           headers=header, only_data=False, https=self.collection.https)

    def unlink_expenses_sheet(self, external_ids_to_unlink):
        """
        Unlink Okticket expenses from expense sheets
        :param external_ids_to_unlink: external_id list char
        """
        expenses_to_unlink = []
        expenses_to_import = []
        for external_id in external_ids_to_unlink:
            # Se recupera el gasto entre los de Odoo por external_id
            okticket_expense = self.env['okticket.hr.expense'].search([('external_id', '=', external_id)])
            if okticket_expense:
                expenses_to_unlink.append(okticket_expense.odoo_id)
            else:
                # Si no está en Odoo se importa de Okticket
                expenses_to_import.append(external_id)
            self.set_report_expense(False, expenses_to_unlink)
        return True

    def link_expenses_sheet(self, sheet_external_id, expenses_to_link):
        """
        Links expenses to indicated expenses sheet
        :param sheet_external_id: Okticket external id of the expense sheet (char)
        :param expenses_to_link: hr.expense list to link to Okticket expense sheet
        """
        return self.set_report_expense(sheet_external_id, expenses_to_link)

    def set_report_expense(self, report_id, expenses):
        expense_backend_adapter = self.component(usage='backend.adapter', model_name='okticket.hr.expense')
        for expense in expenses:
            vals_dict = {
                'company_id': expense.company_id.okticket_company_id,
                'user_id': expense.employee_id.okticket_user_id,
                'report_id': report_id,
            }
            expense_external_id = expense.okticket_bind_ids and expense.okticket_bind_ids[0].external_id or False
            if expense_external_id:
                expense_backend_adapter.write_expense(expense_external_id, vals_dict)

    def search(self, filters=False):
        if self._auth():
            if filters and filters.get('sheet_expense_external_id'):
                result = self.okticket_api.find_report_by_id(filters['sheet_expense_external_id'],
                                                             https=self.collection.https)
            else:
                # Esta implementacion de okticket accede directamente a los metodos de find_expense_sheet
                result = self.okticket_api.find_expense_sheets(https=self.collection.https)
                # Filtra los resultados obtenidos por el campo y valor indicados en el dict de filters
                if filters:
                    filter_result = []
                    for okticket_user in result.get('result', []):
                        valid_result = True
                        for filter_key, filter_val in filters.items():
                            if not filter_key in okticket_user \
                                    or okticket_user[filter_key] != filter_val:
                                # Si no tiene alguno de los filtros o no lo cumple, se excluye
                                valid_result = False
                                break
                        if valid_result:
                            filter_result.append(okticket_user)
                    result['result'] = filter_result
            # Log event
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return []

    # Valid state transition for Okticket expenses sheets
    # key: status_id from expense sheet
    # values: valid action_id that could be apply in this state
    _STATUS_TRANSITIONS = {
        0: [347],
        34: [348, 349, 350],
        3: [354],
        5: [351, 352],
        35: [353],
        36: []
    }

    def change_expense_sheet_status(self, expense_sheets, action_id, comments='No comment'):
        """
        Changes Okticket expenses sheets state through sent action id and Odoo hr.expense.sheet
        :param expense: hr.expense.sheets RecordSet
        :param action_id: Okticket expenses sheet status_id (int)
        """
        expense_sheet_backend_adapter = self.component(usage='backend.adapter',
                                                       model_name='okticket.hr.expense.sheet')
        # Consultar estado actual de hoja de gastos en Okticket
        for sheet in expense_sheets:
            sheet_expense_external_id = sheet.okticket_bind_ids and sheet.okticket_bind_ids[0].external_id or False
            if sheet_expense_external_id:
                filter = {
                    'sheet_expense_external_id': sheet_expense_external_id,
                }
                current_expense_sheet_oktk = expense_sheet_backend_adapter.search(filters=filter)
                if current_expense_sheet_oktk:
                    current_status_id = current_expense_sheet_oktk.get('status_id')
                    # Comprobación de que la acción a realizar sobre hoja de gastos con el status_id actual es válida
                    if action_id in self._STATUS_TRANSITIONS.get(current_status_id, []):
                        # Modificar status de la hoja de gastos
                        expense_sheet_backend_adapter.workflow_expense_sheet(sheet_expense_external_id, action_id,
                                                                             comments=comments)
                    else:
                        _logger.warning(_('Action not valid for Okticket expense sheet %s in state %s'),
                                        sheet_expense_external_id, current_status_id)
        return True

    def workflow_expense_sheet(self, sheet_expense_external_id, action_id, comments='No comment'):
        if self._auth():
            result = self.okticket_api_workflow_expense_sheet(sheet_expense_external_id, action_id, comments=comments)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de workflow
    def okticket_api_workflow_expense_sheet(self, sheet_expense_external_id, action_id, comments='No comment'):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/reports')
        url += '/%s/actions/%s' % (sheet_expense_external_id, action_id)
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        # TODO: qué comentario añadir al cambio de estado ??? POR DEFECTO EL DE POSTMAN
        body = {
            'comment': comments
        }
        return okticketapi.general_request(url, "POST", body, headers=header, only_data=False,
                                           https=self.collection.https)
