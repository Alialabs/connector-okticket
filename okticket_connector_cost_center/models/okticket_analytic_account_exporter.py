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

    def create_cost_center(self, acc_analyt):
        """
        Run the synchronization for all users, using the connector crons.
        """
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        # Mapper
        mapper = self.component(usage='account.analytic.account.exporter')
        # Binder
        binder = self.component(usage='account.analytic.account.binder')
        # Read expenses values from OkTicket
        if acc_analyt:
            sale = False
            for project in acc_analyt.project_ids:
                if project.sale_order_id:
                    sale = project.sale_order_id
                    break

            cost_center_name = acc_analyt.project_ids[0].name
            if acc_analyt.project_ids[0].partner_id:
                cost_center_name += ' - ' + acc_analyt.project_ids[0].partner_id.name
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

    def modify_cc_name(self, acc_analyt):
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        if acc_analyt:
            for ok_acc_an_acc in acc_analyt.okticket_bind_ids:
                cost_center_name = acc_analyt.project_ids[0].name
                if acc_analyt.project_ids[0].partner_id:
                    cost_center_name += ' - ' + acc_analyt.project_ids[0].partner_id.name
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
