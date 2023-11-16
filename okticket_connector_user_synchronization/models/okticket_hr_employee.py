# -*- coding: utf-8 -*-
#
#    Created on 19/07/19
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

from odoo import _, fields, models, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.employee',
        inverse_name='odoo_id',
        string='Hr Employee Bindings',
    )

    def _get_hr_employee(self):
        for employee in self:
            external_ids = [okticket_acc_emp.external_id for okticket_acc_emp in employee.okticket_bind_ids]
            employee.okticket_user_id = external_ids and int(float(external_ids[0])) or -1.0

    def _set_hr_employee(self):
        for employee in self.filtered(lambda emp: emp.okticket_bind_ids):
            employee.okticket_bind_ids.write({'external_id': employee.okticket_user_id})

    def _search_hr_employee(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, int):
            raise ValueError(_('Value should be integer (not %s)'), value)
        domain = []
        odoo_ids = self.env['okticket.hr.employee'].search([
            ('external_id', operator, value)]).mapped('odoo_id').ids
        if odoo_ids:
            domain.append(('id', 'in', odoo_ids))
        return domain

    okticket_user_id = fields.Integer(string="Okticket User_Id",
                                      default=-1.0,
                                      compute=_get_hr_employee,
                                      inverse=_set_hr_employee,
                                      search=_search_hr_employee)

    @api.multi
    def synchronize_record(self, fields=None, **kwargs):
        """ Synchronization with user on Okticket """
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        self.env['okticket.hr.employee'].sudo().import_batch(backend, filters=fields)
        return True


class OkticketHrEmployee(models.Model):
    _name = 'okticket.hr.employee'
    _inherit = 'okticket.binding'
    _inherits = {'hr.employee': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Hr Employee',
        required=True,
        ondelete='cascade',
    )


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    okticket_hr_employee_ids = fields.One2many(
        comodel_name='okticket.hr.employee',
        inverse_name='backend_id',
        string='Hr Employee Bindings',
        context={'active_test': False})


class HrEmployeeAdapter(Component):
    _name = 'okticket.hr.employee.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.hr.employee'

    def search(self, filters=False):
        if self._auth():
            result = self.okticket_api.find_users(https=self.collection.https)
            if filters:
                filter_result = []
                for okticket_user in result.get('result', []):
                    valid_result = True
                    for filter_key, filter_val in filters.items():
                        if not filter_key in okticket_user \
                                or okticket_user[filter_key] != filter_val:
                            valid_result = False
                            break
                    if valid_result:
                        filter_result.append(okticket_user)
                result['result'] = filter_result
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])

            # Si el resultado es un valor True / False (control de errores que no interrumpen ejecución, ej.: 422))
            if isinstance(result['result'], bool):
                return []

            return result['result']
        return []
