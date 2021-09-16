# -*- coding: utf-8 -*-
#
#    Created on 3/07/19
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

from odoo import api, fields, models
from odoo.addons.queue_job.job import job
from odoo.addons.component.core import Component
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.account.analytic.account',
        inverse_name='odoo_id',
        string='Accoutn Analytic Account Bindings',
    )

    def _okticket_create(self):
        '''
        Creates cost center object in OkTicket related with current account.analytic.account
        '''
        return self.env['okticket.account.analytic.account'].sudo().create_cost_center(self)

    def _okticket_unlink(self):
        '''
        Delete cost center object in OkTicket related with current account.analytic.account
        '''
        self.env['okticket.account.analytic.account'].sudo().delete_cost_center(self)

    def _okticket_modify_cc_name(self):
        '''
        Write cost center object in OkTicket related with current account.analytic.account
        '''
        self.env['okticket.account.analytic.account'].sudo().modify_cc_name(self)

    def _okticket_modify_active_state_cost_center(self, new_state):
        '''
        Modify active field of cost center related with project
        :return:
        '''
        self.env['okticket.account.analytic.account'].sudo().modify_active_state_cost_center(self, new_state)


class OkticketAccountAnalyticAccount(models.Model):
    _name = 'okticket.account.analytic.account'
    _inherit = 'okticket.binding'
    _inherits = {'account.analytic.account': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Account Analytic Account',
        required=True,
        ondelete='cascade',
    )

    # TODO : refactorizar exporter con listener y adapter.CRUD (ejemplo a partir de connector_magento_export_partner/models/partner/listener

    @job
    @api.multi
    def create_cost_center(self, acc_analyt):
        """ Create new cost center in OkTicket and relates with an Odoo account.analytic.account"""
        # Default okticket.backend ( si el user es admin, no funciona el metodo anterior de obtención de backend)
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='account.analytic.account.exporter')
                try:
                    return exporter.create_cost_center(acc_analyt)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning('Could not connect to Okticket')
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)

    @job
    @api.multi
    def modify_cc_name(self, acc_analyt):
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='account.analytic.account.exporter')
                try:
                    return exporter.modify_cc_name(acc_analyt)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning('Could not connect to Okticket')
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)

    @job
    @api.multi
    def delete_cost_center(self, acc_analyt):
        """ Delete cost center in OkTicket related with Odoo account.analytic.account that is being unlinked"""
        # Default okticket.backend ( si el user es admin, no funciona el metodo anterior de obtención de backend)
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='account.analytic.account.exporter')
                try:
                    return exporter.delete_cost_center(acc_analyt)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning(_('Could not connect to Okticket'))
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)

    @job
    @api.multi
    def modify_active_state_cost_center(self, acc_analyt, new_state):
        """ Modify cost center active state in OkTicket"""
        # Default okticket.backend ( si el user es admin, no funciona el metodo anterior de obtención de backend)
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='account.analytic.account.exporter')
                try:
                    return exporter.modify_active_state_cost_center(acc_analyt, new_state)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning(_('Could not connect to Okticket'))
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)

class AccountAnalyticAccountAdapter(Component):
    """
    Account Analytic Account Backend Adapter for Okticket
    """

    _name = 'okticket.account.analytic.account.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.account.analytic.account'

    # def search(self, filters):
    #     self._auth()
    #     # Se llama directamente a la abstracción de find con el path de cuentas analiticas
    #     # TODO: abstraer el find() del connector y extenderlo con un find_department()
    #     path = "/departments"
    #     response = self.find(path)
    #     return response

    def create_cost_center(self, values):
        if self._auth():
            result = self.okticket_api_create_cost_center(values)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de create
    def okticket_api_create_cost_center(self, values):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/cost-centers')
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json', }
        fields_dict = {
            "active": True,
            "global": True,
        }
        fields_dict.update(values)
        return okticketapi.general_request(url, "POST", fields_dict,
                                               headers=header, only_data=False, https=self.collection.https)

    def modify_cc_name(self, cost_center_id, values):
        if self._auth():
            result = self.okticket_api_modify_cc_name(cost_center_id, values)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    def okticket_api_modify_cc_name(self, cost_center_id, values):
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/cost-centers')
        url = url + '/' + cost_center_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json', }
        return okticketapi.general_request(url, "PATCH", values,
                                               headers=header, only_data=False, https=self.collection.https)

    def delete_cost_center(self, cost_center_id):
        if self._auth():
            result = self.okticket_api_delete_cost_center(cost_center_id)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de unlink
    def okticket_api_delete_cost_center(self, cost_center_id):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/cost-centers')
        url = url + '/' + cost_center_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        return okticketapi.general_request(url, "DELETE", {},
                                               headers=header, only_data=False, https=self.collection.https)

    def modify_active_state_cost_center(self, cost_center_id, new_state):
        if self._auth():
            result = self.okticket_api_modify_active_state_cost_center(cost_center_id, new_state)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de unlink
    def okticket_api_modify_active_state_cost_center(self, cost_center_id, new_state):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/cost-centers')
        url = url + '/' + cost_center_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        return okticketapi.general_request(url, "PATCH", {'active': new_state,}, headers=header,
                                           only_data=False, https=self.collection.https)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
