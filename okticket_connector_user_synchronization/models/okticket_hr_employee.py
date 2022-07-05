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

from odoo import fields, models, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.employee',
        inverse_name='odoo_id',
        string='Hr Employee Bindings', )

    okticket_user_id = fields.Integer(string="Okticket User Id",
                                      readonly=True)

    @api.multi
    def synchronize_record(self, fields=None, **kwargs):
        """ Synchronization with user on Okticket """
        # TODO: reaprovechar import_batch añadiéndole filtros que se propagan al search()
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


class HrEmployeeAdapter(Component):
    _name = 'okticket.hr.employee.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.hr.employee'

    def search(self, filters=False):
        if self._auth():
            # Esta implementacion de okticket accede directamente a los metodos de find_employees
            result = self.okticket_api.find_users(https=self.collection.https)
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
