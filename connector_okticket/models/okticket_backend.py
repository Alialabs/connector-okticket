# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models
from odoo.exceptions import Warning
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

to_string = fields.Date.to_string


class ConnectorBackend(models.AbstractModel):
    _name = 'connector.backend'
    _inherit = ['collection.base']
    _description = 'Connector Backend'


class OkticketBackend(models.Model):
    _name = 'okticket.backend'  # Collection's name
    _description = 'Okticket Backend Configuration'
    _inherit = 'connector.backend'

    _versions = {
        '1.0': 'okticket.version.key.1.0',
    }

    @api.model
    def _select_versions(self):
        return [('1.0', _('1.0 and higher'))]

    name = fields.Char(string="Label", copy=False)
    location = fields.Char(
        'Location',
        size=128,
        required=True,
    )
    key = fields.Char(
        'Key',
        size=64,
        groups='connector.group_connector_manager',
    )
    version = fields.Selection(
        _select_versions,
        string='Version',
        required=True
    )
    default_lang_id = fields.Many2one(
        'res.lang',
        'Default Language',
        help="If a default language is selected, the records "
             "will be imported in the translation of this language.\n"
             "Note that a similar configuration exists "
             "for each storeview.")
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    okticket_company_id = fields.Integer(string='Okticket Company Id',
                                         related='company_id.okticket_company_id')
    active = fields.Boolean('Active', default=True)
    import_expenses_since = fields.Datetime('Import Expenses since')
    http_client_conn_url = fields.Char(
        'HTTP connection url',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    base_url = fields.Char(
        'Base url',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    image_base_url = fields.Char(
        'Image Base url',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    auth_uri = fields.Char(
        'Oauth path',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    uri_op_path = fields.Char(
        'Operations path',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    api_login = fields.Char(
        'User',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    api_password = fields.Char(
        'Pass',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    grant_type = fields.Char(
        'Grant type',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    oauth_client_id = fields.Char(
        'Oauth client id',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    oauth_secret = fields.Char(
        'Oauth secret',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    scope = fields.Char(
        'Scope',
        size=64,
        required=True,
        groups='connector.group_connector_manager',
    )
    log_event_ids = fields.One2many('log.event', 'backend_id', string='Log Events',
                                    help='Log events related with this backend')
    https = fields.Boolean(string='HTTPS protocol',
                           default=True)

    def get_default_backend_okticket_connector(self):
        """
        :return: backends with 'company_id' like the company of the current user
        """
        default_okticket_backend = self.search([('company_id', '=', self.env.user.company_id.id)])
        return default_okticket_backend and default_okticket_backend[0] or False

    def check_auth(self):
        """
        Check the authentication with Okticket
        """
        self.ensure_one()
        backend_record = self.env['okticket.backend'].browse(self.id)
        with backend_record.work_on('okticket.backend') as work:
            adapter = work.component(usage='backend.adapter')
        try:
            adapter._auth()
        except Exception as e:
            _logger.error('Exception: %s\n', e)
            import traceback
            traceback.print_exc()
            raise Warning(_('Could not connect to Okticket'))
        raise Warning(
            _('Connection test succeeded\n'
              'Everything seems properly set up'))

    @api.model
    def _scheduler_import_expenses(self):
        for backend_record in self.search([]):
            _logger.info(
                'Scheduling expenses batch import from Okticket '
                'with backend %s.' % backend_record.name)
            backend_record.import_expenses()

    def import_expenses(self):
        self.ensure_one()
        self.env['okticket.hr.expense'].sudo().import_batch(self)
        return True
