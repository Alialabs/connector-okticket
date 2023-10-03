# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.addons.component.core import Component
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.account.analytic.account',
        inverse_name='odoo_id',
        string='Account Analytic Account Bindings',
    )

    def generate_cost_center_name_from_analytic(self):
        self.ensure_one()
        cost_center_name = self.name
        if self.partner_id:
            cost_center_name += ' - ' + self.partner_id.name
        return cost_center_name

    def _get_cost_center(self):
        for analytic in self:
            external_ids = [okticket_acc_an.external_id for okticket_acc_an in analytic.okticket_bind_ids]
            analytic.okticket_cost_center_id = external_ids and int(float(external_ids[0])) or -1.0

    def _set_cost_center(self):
        for analytic in self.filtered(lambda cc: cc.okticket_bind_ids):
            analytic.okticket_bind_ids.write({'external_id': analytic.okticket_cost_center_id})

    def _search_cost_center(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, int):
            raise ValueError(_('Value should be integer (not %s)'), value)
        domain = []
        odoo_ids = self.env['okticket.account.analytic.account'].search([
            ('external_id', operator, value)]).mapped('odoo_id').ids
        if odoo_ids:
            domain.append(('id', 'in', odoo_ids))
        return domain

    okticket_cost_center_id = fields.Integer(string="OkTicket Cost_center_id",
                                             default=-1.0,
                                             compute=_get_cost_center,
                                             inverse=_set_cost_center,
                                             search=_search_cost_center)

    def _okticket_create_duplicates_control(self):
        """
        Creates/link cost center object in OkTicket related with current account.analytic.account.
        Checks if exists cost center in OkTicket and avoid automatic creation.
        """
        return self.env['okticket.account.analytic.account'].sudo().create_cost_center_duplicates_control(self)

    def _okticket_create(self):
        """
        Creates cost center object in OkTicket related with current account.analytic.account
        """
        return self.env['okticket.account.analytic.account'].sudo().create_cost_center(self)

    def _okticket_unlink(self):
        """
        Delete cost center object in OkTicket related with current account.analytic.account
        """
        self.env['okticket.account.analytic.account'].sudo().delete_cost_center(self)

    def _okticket_modify_cc_name(self):
        """
        Write cost center object in OkTicket related with current account.analytic.account
        """
        self.env['okticket.account.analytic.account'].sudo().modify_cc_name(self)

    def _okticket_modify_active_state_cost_center(self, new_state):
        """
        Modify active field of cost center related with project
        :return:
        """
        self.env['okticket.account.analytic.account'].sudo().modify_active_state_cost_center(self, new_state)

    def unlink_cost_center_from_analytic_account(self):
        for record in self:
            record.okticket_bind_ids = [(2, ok_bind.id) for ok_bind in record.okticket_bind_ids]


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

    def create_cost_center_duplicates_control(self, acc_analyt):
        """
        Create new cost center in OkTicket and relates with an Odoo account.analytic.account.
        Checks and inform about cost center duplicates.
        """
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        if backend:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='account.analytic.account.exporter')
                try:
                    return exporter.create_cost_center_duplicates_control(acc_analyt)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise (e or UserError(_('Could not connect to Okticket')))
        else:
            _logger.warning(_('WARNING! Not exists backend for company %s (%s)'),
                            self.env.user.company_id.name, self.env.user.company_id.id)

    def create_cost_center(self, acc_analyt):
        """ Create new cost center in OkTicket and relates with an Odoo account.analytic.account """
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
                    raise (e or UserError(_('Could not connect to Okticket')))
        else:
            _logger.warning(_('WARNING! Not exists backend for company %s (%s)'),
                            self.env.user.company_id.name, self.env.user.company_id.id)

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
                    raise (e or UserError(_('Could not connect to Okticket')))
        else:
            _logger.warning(_('WARNING! Not exists backend for company %s (%s)'),
                            self.env.user.company_id.name, self.env.user.company_id.id)

    def delete_cost_center(self, acc_analyt):
        """ Delete cost center in OkTicket related with Odoo account.analytic.account that is being unlinked """
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
                    raise (e or UserError(_('Could not connect to Okticket')))
        else:
            _logger.warning(_('WARNING! Not exists backend for company %s (%s)'),
                            self.env.user.company_id.name, self.env.user.company_id.id)

    def modify_active_state_cost_center(self, acc_analyt, new_state):
        """ Modify cost center active state in OkTicket"""
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
                    raise (e or UserError(_('Could not connect to Okticket')))
        else:
            _logger.warning(_('WARNING! Not exists backend for company %s (%s)'),
                            self.env.user.company_id.name, self.env.user.company_id.id)


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    okticket_analytic_account_ids = fields.One2many(
        comodel_name='okticket.account.analytic.account',
        inverse_name='backend_id',
        string='Analytic Account Bindings',
        context={'active_test': False})


class AccountAnalyticAccountAdapter(Component):
    """
    Account Analytic Account Backend Adapter for Okticket
    """

    _name = 'okticket.account.analytic.account.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.account.analytic.account'

    def search(self, filters=False):
        if self._auth():
            result = self.okticket_api.find_cost_center(params=filters, https=self.collection.https)

            # Log event
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

    def okticket_api_create_cost_center(self, values):
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

    def okticket_api_create_cost_center(self, values):
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

    def okticket_api_delete_cost_center(self, cost_center_id):
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

    def okticket_api_modify_active_state_cost_center(self, cost_center_id, new_state):
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/cost-centers')
        url = url + '/' + cost_center_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        return okticketapi.general_request(url, "PATCH", {'active': new_state, }, headers=header,
                                           only_data=False, https=self.collection.https)
