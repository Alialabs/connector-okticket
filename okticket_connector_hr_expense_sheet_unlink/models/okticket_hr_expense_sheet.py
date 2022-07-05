# -*- coding: utf-8 -*-
#
#    Created on 09/06/22
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

from odoo import api, fields, models, _
from odoo.addons.component.core import Component
import logging

_logger = logging.getLogger(__name__)


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def delete_expense_sheet(self):
        """Delete related expense sheet in Okticket"""
        self.env['okticket.hr.expense.sheet'].sudo().delete_expense_sheet(self)
        return True


class OkticketHrExpenseSheet(models.Model):
    _inherit = 'okticket.hr.expense.sheet'

    @api.multi
    def delete_expense_sheet(self, exp_sheet):
        """ Delete expense sheet in OkTicket related with Odoo hr.expense.sheet that is being unlinked"""
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='record.exporter')
                try:
                    return exporter.delete_expense_sheet(exp_sheet)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning(_('Could not connect to Okticket'))
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)


class HrExpenseSheetAdapter(Component):
    _inherit = 'okticket.hr.expense.sheet.adapter'

    def delete_expense_sheet(self, expense_sheet_id):
        if self._auth():
            result = self.okticket_api_delete_expense_sheet(expense_sheet_id)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de unlink
    def okticket_api_delete_expense_sheet(self, expense_sheet_id):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/reports')
        url = url + '/' + expense_sheet_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        return okticketapi.general_request(url, "DELETE", {},
                                           headers=header, only_data=False, https=self.collection.https)
