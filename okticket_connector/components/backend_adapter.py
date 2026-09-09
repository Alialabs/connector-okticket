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

# Live API connectors per (database, backend), so a token survives across the
# many adapter calls of a single synchronisation instead of being thrown away
# after each one. Tokens are not transactional data, so sharing them beyond the
# current cursor is safe; the credentials fingerprint below is what guarantees a
# backend edit is never served a stale token.
_API_CACHE = {}

_AUTH_FIELDS = (
    'http_client_conn_url', 'base_url', 'auth_uri', 'uri_op_path', 'api_login',
    'api_password', 'grant_type', 'oauth_client_id', 'oauth_secret', 'scope',
    'okticket_company_id',
)


def _credentials_fingerprint(auth_data):
    """Identity of the credentials in use, to invalidate the cache on any edit."""
    return tuple(str(auth_data.get(field) or '') for field in _AUTH_FIELDS)


class OkticketBaseBackendAdapter(AbstractComponent):
    _name = 'okticket.base.backend.adapter'
    _inherit = 'base.okticket.connector'
    _usage = 'backend.adapter'


class OkticketAdapter(Component):
    _name = 'okticket.adapter'
    _inherit = 'okticket.base.backend.adapter'
    _usage = 'backend.adapter'

    def _auth(self, force=False):
        """Make a connector with a usable token available as ``self.okticket_api``.

        This used to perform a full OAuth login on every call, building a brand
        new connector each time so even the in-memory token was discarded. Every
        API operation therefore cost two round-trips, halving the throughput of
        an import and doubling the consumption of the documented per-minute call
        limit. The token is now reused while it stays fresh, renewed through the
        refresh grant when it does not, and re-logged from scratch only when
        there is nothing reusable left.

        :param force: skip the cache and authenticate for real. Used by the
            backend's *Authentication test*, which must exercise the
            credentials rather than confirm a token obtained earlier.
        """
        auth_data = self.backend_record.read(['location', 'http_client_conn_url', 'base_url', 'auth_uri',
                                              'api_login', 'api_password', 'uri_op_path', 'okticket_company_id',
                                              'grant_type', 'oauth_client_id', 'oauth_secret', 'scope'])[0]

        cache_key = (self.env.cr.dbname, self.backend_record.id)
        fingerprint = _credentials_fingerprint(auth_data)
        cached = _API_CACHE.get(cache_key)
        if cached and cached[0] != fingerprint:
            # Credentials changed under us: the cached token belongs to the old
            # ones and must not be reused.
            cached = None
            _API_CACHE.pop(cache_key, None)

        if not force and cached and cached[1].token_is_fresh():
            self.okticket_api = cached[1]
            return True

        okticket_api = cached[1] if cached else \
            ticket_connector.OkTicketOpenConnector(params=auth_data)
        if force:
            okticket_api._clear_token()

        try:
            result = okticket_api.authenticate(https=self.backend_record.https)

            # Log event. authenticate() returns None when the token already held
            # was still valid, and there is nothing to report in that case.
            if result is not None:
                result['log'].update({
                    'backend_id': self.collection.id,
                    'type': result['log'].get('type') or 'success',
                    'tag': 'AUTH',
                })
                self.env['log.event'].add_event(result['log'])
                if result['log'].get('type') == 'error':
                    _API_CACHE.pop(cache_key, None)
                    return False

        except (exceptions.AuthError, ConnectionError) as err:
            _API_CACHE.pop(cache_key, None)
            raise FailedJobError(
                _('Okticket connection Error: '
                  'Invalid authentications key.'))

        except (exceptions.UnknownError, exceptions.ServerError) as err:
            _API_CACHE.pop(cache_key, None)
            raise NetworkRetryableError(
                _('A network error caused the failure of the job: '
                  '%s') % ustr(err))

        _API_CACHE[cache_key] = (fingerprint, okticket_api)
        self.okticket_api = okticket_api
        return True

    def search(self, filters):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError
