# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo.addons.component.core import AbstractComponent
from odoo.addons.component.core import Component
from odoo.addons.connector.exception import NetworkRetryableError
from odoo.addons.queue_job.exception import FailedJobError
from odoo.tools import ustr
from odoo.tools.translate import _
from requests.exceptions import ConnectionError

from ..okticket import exceptions, ticket_connector

_logger = logging.getLogger(__name__)


class OkticketBaseBackendAdapter(AbstractComponent):
    _name = 'okticket.base.backend.adapter'
    _inherit = 'base.okticket.connector'
    _usage = 'backend.adapter'


class OkticketAdapter(Component):
    _name = 'okticket.adapter'
    _inherit = 'okticket.base.backend.adapter'
    _usage = 'backend.adapter'

    def _auth(self):
        auth_data = self.backend_record.read(['location', 'http_client_conn_url', 'base_url', 'auth_uri',
                                              'api_login', 'api_password', 'uri_op_path', 'okticket_company_id',
                                              'grant_type', 'oauth_client_id', 'oauth_secret', 'scope'])[0]

        try:
            okticket_api = ticket_connector.OkTicketOpenConnector(params=auth_data)
            result = okticket_api.login(https=self.backend_record.https)

            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
                'tag': 'AUTH',
            })
            self.env['log.event'].add_event(result['log'])
            if result['log'].get('type') == 'error':
                return False

        except (exceptions.AuthError, ConnectionError) as err:
            raise FailedJobError(
                _('Okticket connection Error: '
                  'Invalid authentications key.'))

        except (exceptions.UnknownError, exceptions.ServerError) as err:
            raise NetworkRetryableError(
                _('A network error caused the failure of the job: '
                  '%s') % ustr(err))

        self.okticket_api = okticket_api
        return True

    def search(self, filters):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError
