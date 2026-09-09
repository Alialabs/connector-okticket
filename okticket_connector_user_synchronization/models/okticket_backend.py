# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    @api.model
    def _scheduler_import_employee(self):
        for backend_record in self.search([]):
            _logger.info(
                'Scheduling employees batch import from Okticket '
                'with backend %s.' % backend_record.name)
            backend_record.with_company(backend_record.company_id).import_employees()

    def import_employees(self):
        self.ensure_one()
        # Pass the company-aware backend: components take their env from the
        # backend record (WorkContext.env is collection.env), so the with_company
        # applied to the model alone was discarded for every component.
        self.env['okticket.hr.employee'].sudo().import_batch(
            self.with_company(self.company_id)
        )
        return True
