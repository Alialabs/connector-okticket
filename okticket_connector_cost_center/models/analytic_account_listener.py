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
        """The project's company, else its analytic account's, else the current one.

        Projects have no company by default in a single-company database, so
        reading ``record.company_id`` alone meant the automatic creation never
        fired there.
        """
        if record.company_id:
            return record.company_id
        if record.analytic_account_id and record.analytic_account_id.company_id:
            return record.analytic_account_id.company_id
        return self.env.company

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        if self._get_company_from_record(record).create_cost_center_automatically:
            record.analytic_account_id._okticket_create()

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if 'name' in fields:
            record.analytic_account_id.name = record.name
            record.analytic_account_id._okticket_modify_cc_name()
