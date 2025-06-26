# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if

class AccountAnalyticCostCenterBindingExportListener(Component):
    _name = 'account.analytic.account.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['project.project']


    def _get_company_from_record(self, record):
        """Método auxiliar para obtener la compañía de un registro"""
        # Intentar obtener company_id directamente
        if hasattr(record, 'company_id') and record.company_id:
            return record.company_id

        # Si no existe, intentar a través de account_id
        if hasattr(record, 'account_id') and record.account_id and record.account_id.company_id:
            return record.account_id.company_id

        # Fallback: usar la compañía del usuario actual
        return self.env.company

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        company_id = self._get_company_from_record(record)
        if company_id.create_cost_center_automatically:
            record.account_id._okticket_create()

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if 'name' in fields:
            record.account_id.name = record.name
            record.account_id._okticket_modify_cc_name()
