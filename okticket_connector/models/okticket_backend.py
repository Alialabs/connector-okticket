# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

class ConnectorBackend(models.AbstractModel):
    _name = 'connector.backend'
    _inherit = ['collection.base']
    _description = 'Connector Backend'


class OkticketBackend(models.Model):
    _name = 'okticket.backend'
    _description = 'Okticket Backend Configuration'
    _inherit = 'connector.backend'

    _versions = {
        '1.0': 'okticket.version.key.1.0',
    }

    name = fields.Char(string="Label", copy=False)
    location = fields.Char(string='Location', size=128, required=True)
    key = fields.Char(string='Key', size=64, groups='connector.group_connector_manager')
    version = fields.Selection(selection='_select_versions', string='Version', required=True)
    default_lang_id = fields.Many2one('res.lang', string='Default Language', help=(
        "The language every scheduled run of this backend works in: the log "
        "entries, the reasons written on the expenses and the names of the "
        "expense sheets, which travel to OkTicket as the report name.\n\n"
        "It has to be stated here and not inherited from whoever starts the "
        "run. Odoo's \"Run manually\" button replaces the whole context, so a "
        "job launched from the interface carries no language and writes "
        "everything in English, while the same job launched by the scheduler "
        "writes it in Spanish. Nothing should depend on which button was "
        "pressed.\n\n"
        "Left empty, the company's language is used, and failing that the "
        "one of the user the job runs as."
    ))
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    okticket_company_id = fields.Integer(string='Okticket Company Id', related='company_id.okticket_company_id')
    active = fields.Boolean('Active', default=True)
    import_expenses_since = fields.Datetime('Import Expenses since')
    http_client_conn_url = fields.Char(string='HTTP connection url', size=64, required=True, groups='connector.group_connector_manager')
    base_url = fields.Char(string='Base url', size=64, required=True, groups='connector.group_connector_manager')
    image_base_url = fields.Char(string='Image Base url', size=64, required=True, groups='connector.group_connector_manager')
    auth_uri = fields.Char(string='Oauth path', size=64, required=True, groups='connector.group_connector_manager')
    uri_op_path = fields.Char(string='Operations path', size=64, required=True, groups='connector.group_connector_manager')
    api_login = fields.Char(string='User', size=64, required=True, groups='connector.group_connector_manager')
    api_password = fields.Char(string='Pass', size=64, required=True, groups='connector.group_connector_manager')
    grant_type = fields.Char(string='Grant type', size=64, required=True, groups='connector.group_connector_manager')
    oauth_client_id = fields.Char(string='Oauth client id', size=64, required=True, groups='connector.group_connector_manager')
    oauth_secret = fields.Char(string='Oauth secret', size=64, required=True, groups='connector.group_connector_manager')
    scope = fields.Char(string='Scope', size=64, required=True, groups='connector.group_connector_manager')
    log_event_ids = fields.One2many('log.event', 'backend_id', string='Log Events', help='Log events related with this backend')
    https = fields.Boolean(string='HTTPS protocol', default=True)

    # Expenses import config
    ignore_import_expenses_since = fields.Boolean(string='Ignore Import Expenses Since', default=False)
    import_only_reviewed_expenses = fields.Boolean(
        string='Import Only Reviewed Expenses',
        default=False,
        help='Off by default: every expense OkTicket serves is imported. '
             'Turned on, only the ones already marked as reviewed come in, '
             'which on a company that does not use the review step means '
             'importing almost nothing without any error to explain it.')

    @api.model
    def _select_versions(self):
        return [('1.0', _('1.0 and higher'))]

    def get_default_backend_okticket_connector(self, company=False):
        """
        Get backends with 'company_id' like the company of the current user.
        :return: okticket.backend record or False
        """
        if company:
            backend = self.search([('company_id', '=', company.id)], limit=1)
        else:
            backend = False
        return backend

    def check_auth(self):
        """
        Check the authentication with Okticket.
        """
        self.ensure_one()
        backend_record = self.env['okticket.backend'].browse(self.id)
        with backend_record.work_on('okticket.backend') as work:
            adapter = work.component(usage='backend.adapter')
        try:
            # force=True: the token cache would otherwise let a test pass on
            # credentials that were just edited to something invalid.
            adapter._auth(force=True)
        except Exception as e:
            _logger.error('Exception: %s\n', e)
            import traceback
            traceback.print_exc()
            raise (e or UserError(_('Could not connect to Okticket')))
        raise UserError(_('Connection test succeeded\nEverything seems properly set up'))

    @api.model
    def okticket_work_lang(self):
        """The language this backend's work is written in.

        :return: a language code, or False when nothing states one.
        """
        self.ensure_one()
        return (self.default_lang_id.code
                or self.company_id.partner_id.lang
                or self.env.user.lang
                or self.env.context.get('lang'))

    def okticket_work_env(self):
        """This backend, bound to the company and the language of its work.

        Every scheduled entry point goes through here, so a run started from
        the "Run manually" button produces exactly what the scheduler would:
        Odoo's ``method_direct_trigger`` replaces the context instead of
        extending it, and what got lost on the way was the language.
        """
        self.ensure_one()
        backend = self.with_company(self.company_id)
        lang = backend.okticket_work_lang()
        return backend.with_context(lang=lang) if lang else backend

    def _scheduler_import_expenses(self):
        """
        Schedule expenses batch import from Okticket.
        """
        for backend_record in self.search([]):
            _logger.info('Scheduling expenses batch import from Okticket with backend %s.', backend_record.name)
            backend_record.okticket_work_env().import_expenses()

    def import_expenses(self):
        """
        Import expenses from Okticket.
        """
        self.ensure_one()
        # Pass the company-aware backend: components take their env from the
        # backend record (WorkContext.env is collection.env), so the with_company
        # applied to the model alone was discarded for every component.
        self.env['okticket.hr.expense'].sudo().import_batch(
            self.with_company(self.company_id)
        )
        return True
