# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    @api.model
    def _scheduler_synchronize_products(self):
        for backend_record in self.search([]):
            _logger.info(
                'Scheduling product batch synchronization from Okticket '
                'with backend %s.' % backend_record.name)
            # with_company is mandatory here: invoice_prod_id / rebillable_prod_id
            # are company_dependent, so without it the base->invoice links are
            # written under the cron user's company while the expense importer
            # reads them under the backend's company. Any non-default company
            # then resolved no product for "Factura" expenses and dropped them.
            backend_record.with_company(backend_record.company_id).synchronize_products()

    def synchronize_products(self):
        self.ensure_one()
        # Pass the company-aware backend: components take their env from the
        # backend record (WorkContext.env is collection.env), so a with_company
        # applied only to the model here would be discarded.
        self.env['okticket.product.template'].sudo().import_batch(
            self.with_company(self.company_id)
        )
        return True
