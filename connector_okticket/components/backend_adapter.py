# -*- coding: utf-8 -*-
#
#    Created on 16/04/19
#
#    @author:alia
#
#
# 2019 ALIA Technologies
#       http://www.alialabs.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from odoo.tools.translate import _
from odoo.tools import ustr
from requests.exceptions import ConnectionError
from odoo.addons.component.core import Component
from ..okticket import exceptions, ticket_connector
from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import FailedJobError
from odoo.addons.connector.exception import NetworkRetryableError
import logging

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
