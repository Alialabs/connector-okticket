# -*- coding: utf-8 -*-
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
            backend_record.synchronize_products()

    def synchronize_products(self):
        self.ensure_one()
        self.env['okticket.product.template'].sudo().import_batch(self)
        return True
