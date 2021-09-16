# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import fields, models
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
            return result['result']
        return []
