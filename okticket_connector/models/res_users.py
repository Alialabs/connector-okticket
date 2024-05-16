# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    okticket_backend_ids = fields.Many2many(
        'okticket.backend', string='Okticket Server',
        help="The okticket service from which to import "
             "your timesheets. If empty, the default okticket service "
             "will be used instead.")

    # Fixed with https://www.odoo.com/es_ES/forum/ayuda-1/my-profile-gives-access-error-for-employee-fields-167590
    def __init__(self, *args):
        super(ResUsers, self).__init__(*args)
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['okticket_backend_ids'])
