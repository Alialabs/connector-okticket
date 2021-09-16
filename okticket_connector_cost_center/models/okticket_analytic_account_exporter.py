# -*- coding: utf-8 -*-
#
#    Created on 2/05/19
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
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticAccountExporter(Component):
    _name = 'okticket.account.analytic.account.exporter'
    _inherit = 'okticket.export.mapper'
    _apply_on = 'okticket.account.analytic.account'
    _usage = 'account.analytic.account.exporter'

#TODO : refactorizar con listener y adapter.CRUD (ejemplo a partir de connector_magento_export_partner/models/partner/listener

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
                _logger.info(
                    'Created new Cost Center in Okticket !!!')

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
        _logger.info(
            'Modified Cost Center name in Okticket !!!')

    def delete_cost_center(self, acc_analyt):
        """
        Run the synchronization for all users, using the connector crons.
        """
        backend_adapter = self.component(usage='backend.adapter')
        # mapper = self.component(usage='account.analytic.account.exporter')
        # binder = self.component(usage='account.analytic.account.binder')
        # okticket_company_id = self.env.user.company_id.okticket_company_id
        if acc_analyt:
            # Eliminar cost_center
            ok_acc_an_acc_ids = [ okticket_cc.id for okticket_cc in acc_analyt ]
            for ok_acc_an_acc in self.env['okticket.account.analytic.account'].\
                        search([('odoo_id', 'in', ok_acc_an_acc_ids)]):
                try:
                    backend_adapter.delete_cost_center(ok_acc_an_acc.external_id)
                except Exception as e:
                    _logger.error('\n\n    >>> ERROR ELIMINACION GASTO ID: %s no localizacdo en OKTICKET\n',
                                  ok_acc_an_acc.external_id)
        _logger.info(
            'Delete related Cost Center in Okticket !!!')

    def modify_active_state_cost_center(self, acc_analyt, new_state):
        """
        Run the synchronization for all users, using the connector crons.
        """
        backend_adapter = self.component(usage='backend.adapter')
        # mapper = self.component(usage='account.analytic.account.exporter')
        # binder = self.component(usage='account.analytic.account.binder')
        # okticket_company_id = self.env.user.company_id.okticket_company_id
        if acc_analyt:
            # Modiy cost_center active field
            ok_acc_an_acc_ids = [ okticket_cc.id for okticket_cc in acc_analyt ]
            for ok_acc_an_acc in self.env['okticket.account.analytic.account'].\
                        search([('odoo_id', 'in', ok_acc_an_acc_ids)]):
                backend_adapter.modify_active_state_cost_center(ok_acc_an_acc.external_id, new_state)
        _logger.info(
            'Modify related Cost Center in Okticket !!!')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: