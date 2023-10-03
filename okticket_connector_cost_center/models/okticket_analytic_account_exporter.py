# -*- coding: utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo.addons.component.core import Component
from odoo import _

_logger = logging.getLogger(__name__)


class AccountAnalyticAccountExporter(Component):
    _name = 'okticket.account.analytic.account.exporter'
    _inherit = 'okticket.export.mapper'
    _apply_on = 'okticket.account.analytic.account'
    _usage = 'account.analytic.account.exporter'

    def create_cost_center_duplicates_control(self, acc_analyt):
        """
        Creates cost center in Okticket from Odoo data with control system
        """
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        # Mapper
        mapper = self.component(usage='account.analytic.account.exporter')
        # Binder
        binder = self.component(usage='account.analytic.account.binder')

        result = True
        if acc_analyt:
            cost_center_name = acc_analyt.generate_cost_center_name_from_analytic()
            # Comprueba si existe un cost center con el mismo nombre
            if backend_adapter.search({'name': cost_center_name}):
                result = False  # Si existe al menos algún cost center con el mismo nombre,
                # retorna un False que es posteriormente procesado en el método cost_center_from_analytic_confirm()
            else:
                # Si no existe ningún cost center con el nombre indicado, se crea de forma regular
                result = self.create_cost_center(acc_analyt)
        return result

    def create_cost_center(self, acc_analyt):
        """
        Creates cost center in Okticket from Odoo data
        """
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        # Mapper
        mapper = self.component(usage='account.analytic.account.exporter')
        # Binder
        binder = self.component(usage='account.analytic.account.binder')

        if acc_analyt:
            sale = acc_analyt.get_related_sale_order()
            cost_center_name = acc_analyt.generate_cost_center_name_from_analytic()
            okticket_company_id = acc_analyt.company_id and acc_analyt.company_id.okticket_company_id

            values = {
                'name': cost_center_name,
                'code': sale and sale.name or '',
                'company_id': okticket_company_id,
                'active': True,
                'global': True,
            }
            new_cost_center_vals = backend_adapter.create_cost_center(values)
            if new_cost_center_vals:
                new_cost_center_id = new_cost_center_vals and new_cost_center_vals.get('data') \
                                     and new_cost_center_vals['data'].get('id')
                self.env['okticket.account.analytic.account'].create({
                    'odoo_id': acc_analyt.id,
                    'backend_id': self.collection.id,
                    'external_id': str(new_cost_center_id),
                })
                _logger.info(_('Created new Cost Center in Okticket'))
        return True

    def modify_cc_name(self, acc_analyt):
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        if acc_analyt:
            for ok_acc_an_acc in acc_analyt.okticket_bind_ids:
                cost_center_name = acc_analyt.name
                if acc_analyt.partner_id:
                    cost_center_name += ' - ' + acc_analyt.partner_id.name
                values = {
                    'name': cost_center_name,
                }
                new_cost_center_vals = backend_adapter.modify_cc_name(ok_acc_an_acc.external_id, values)
        _logger.info(_('Modified new Cost Center in Okticket'))

    def delete_cost_center(self, acc_analyt):
        """
        Run the synchronization for all users, using the connector crons.
        """
        backend_adapter = self.component(usage='backend.adapter')
        if acc_analyt:
            # Delete cost_center
            ok_acc_an_acc_ids = [okticket_cc.id for okticket_cc in acc_analyt]
            for ok_acc_an_acc in self.env['okticket.account.analytic.account']. \
                    search([('odoo_id', 'in', ok_acc_an_acc_ids)]):
                try:
                    backend_adapter.delete_cost_center(ok_acc_an_acc.external_id)
                except Exception as e:
                    _logger.error(_('Error deleting expense ID: %s not located in Okticket'),
                                  ok_acc_an_acc.external_id)
        _logger.info(_('Deleted Cost Center in Okticket'))

    def modify_active_state_cost_center(self, acc_analyt, new_state):
        """
        Run the synchronization for all users, using the connector crons.
        """
        backend_adapter = self.component(usage='backend.adapter')
        if acc_analyt:
            # Modify cost_center active field
            ok_acc_an_acc_ids = [okticket_cc.id for okticket_cc in acc_analyt]
            for ok_acc_an_acc in self.env['okticket.account.analytic.account']. \
                    search([('odoo_id', 'in', ok_acc_an_acc_ids)]):
                backend_adapter.modify_active_state_cost_center(ok_acc_an_acc.external_id, new_state)
        _logger.info(_('Modified new Cost Center in Okticket'))
