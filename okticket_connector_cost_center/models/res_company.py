# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    create_cost_center_automatically = fields.Boolean(
        'Auto-create project cost center',
        help='When enabled, creating a project in Odoo automatically creates '
             'its cost center in OkTicket (renames, archives and deletions '
             'are synchronized too).')
