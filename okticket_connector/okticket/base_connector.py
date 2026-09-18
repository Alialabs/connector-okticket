import http.client
import json
import logging
import time
import urllib.parse
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from .exceptions import (
    BaseOkticketError,
    AuthError,
    ConflictError,
    ImpersonateError,
    RateLimitError,
    ServerError,
    ValidationError,
    ResourceNotFoundError,
    RequestEntityTooLargeError,
    UnknownError,
    ForbiddenError,
    JSONDecodeError,
    GatewayError,
)

# Attempts to recover from a recoverable transport error (401 token expiry,
# 429 rate limit, dropped connection) before giving up on a request.
MAX_REQUEST_RETRIES = 3
# Fallback back-off per attempt when the API does not send Retry-After. The
# documented limit resets every minute, hence the last step.
RATE_LIMIT_BACKOFF = (5, 20, 60)
# Back-off per attempt after a dropped connection. Shorter than the rate limit
# one: nothing has to expire, the connection just has to be reopened.
TRANSPORT_BACKOFF = (2, 5, 15)
# Seconds subtracted from the reported token lifetime, so a token is renewed
# before it expires mid-request instead of costing a 401 and a retry.
TOKEN_EXPIRY_MARGIN = 60
# Socket timeout for every API call. http.client otherwise falls back to the
# global default socket timeout, normally None, so a stalled connection would
# block the import indefinitely instead of failing and being retried.
REQUEST_TIMEOUT = 120


def _parse_retry_after(response):
    """Seconds to wait from a 429 response, or None when not reported."""
    for header in ('Retry-After', 'X-RateLimit-Reset'):
        raw = response.getheader(header)
        if raw:
            try:
                return max(1, int(float(raw)))
            except (TypeError, ValueError):
                continue
    return None


def _auth_error_message(url):
    return ('Okticket rejected the credentials (401) for %s. Check the backend '
            'user, password, OAuth client id and secret.' % url)


class BaseConnector:
    def __init__(self):
        self.http_client_conn_url = ""
        self.base_url = ""
        self.auth_uri = ""
        self.uri_op_path = ""
        self.token_type = ""
        self.access_token = ""
        self.refresh_token = ""
        # True when the last paginated listing stopped on an error instead of
        # reaching its end, so the caller knows the result is incomplete.
        self.last_listing_truncated = False
        # Absolute time after which the access token must be renewed. 0 means
        # "unknown", which happens when the API omits expires_in.
        self.token_expires_at = 0
        self.okticket_company_id = ""
        self.backend_id = False
        self.https = False

    def get_login_values(self):
        return {}

    def login_header_generator(self, payload=False):
        return {
            'Content-Type': "application/json",
            'cache-control': "no-cache",
        }

    def get_refresh_values(self):
        """Payload for the refresh-token grant.

        ``grant_type`` must be the literal ``refresh_token`` and not the
        backend's configured grant type (which is ``password``), otherwise this
        would just be a full login wearing a different name.
        """
        return {
            'grant_type': 'refresh_token',
            'client_id': self.oauth_client_id,
            'client_secret': self.oauth_secret,
            'refresh_token': self.refresh_token,
            'scope': self.scope,
        }

    def _store_token(self, result):
        """Keep the whole token triplet from a token-endpoint response.

        The refresh token used to be dropped here even though ``__init__``
        declared it and the API always sends it, which made the refresh grant
        impossible and forced a full login on every single call.
        """
        self.token_type = result.get('token_type') or self.token_type
        self.access_token = result.get('access_token') or ""
        self.refresh_token = result.get('refresh_token') or ""
        try:
            expires_in = int(result.get('expires_in') or 0)
        except (TypeError, ValueError):
            expires_in = 0
        self.token_expires_at = (
            time.time() + max(0, expires_in - TOKEN_EXPIRY_MARGIN) if expires_in else 0
        )

    def _clear_token(self):
        self.token_type = ""
        self.access_token = ""
        self.refresh_token = ""
        self.token_expires_at = 0

    def token_is_fresh(self):
        """Whether the token in hand can still be used.

        When the API does not report ``expires_in`` the lifetime is unknown, so
        the token is assumed usable and the 401 recovery in ``general_request``
        is left to deal with expiry. That is deliberate: the documentation warns
        the 30-minute lifetime "puede variar", so the clock is a hint, never the
        authority.
        """
        if not self.access_token:
            return False
        if not self.token_expires_at:
            return True
        return time.time() < self.token_expires_at

    def login(self, https=False):
        """
        User login. Stores token_type, access_token and refresh_token
        """
        fields_dict = self.get_login_values()
        response = self.general_request(
            self.base_url + self.auth_uri, "POST", fields_dict,
            header_gen_method=self.login_header_generator, only_data=False, https=https
        )
        if response and response.get('result'):
            self._store_token(response['result'])
        return response

    def refresh(self, https=False):
        """Renew the access token with the refresh grant, falling back to login.

        The documentation is explicit that using a refresh token revokes the
        previous pair, and that replaying a spent one answers "The refresh token
        is invalid.". So a failed refresh leaves nothing reusable: the stored
        triplet is dropped and a full login is performed instead of surfacing an
        error the caller cannot act on.
        """
        if not self.refresh_token:
            return self.login(https=https)
        try:
            response = self.general_request(
                self.base_url + self.auth_uri, "POST", self.get_refresh_values(),
                header_gen_method=self.login_header_generator, only_data=False, https=https
            )
        except Exception as exc:
            _logger.info('Okticket refresh token rejected (%s); falling back to login', exc)
            response = None
        result = (response or {}).get('result') or {}
        if not result.get('access_token'):
            self._clear_token()
            return self.login(https=https)
        self._store_token(result)
        return response

    def authenticate(self, https=False):
        """Make sure a usable token is in hand, as cheaply as possible.

        Returns the token-endpoint response when a call was actually needed, or
        None when the token already held is still fresh. Callers log the former
        and skip the latter, which is what keeps the connector log readable.
        """
        if self.token_is_fresh():
            return None
        if self.refresh_token:
            return self.refresh(https=https)
        return self.login(https=https)

    def get_full_path(self, path):
        return self.base_url + self.uri_op_path + path

    def find_header_generator(self, params):
        return {
            'Authorization': f"{self.token_type} {self.access_token}",
            'Accept': "application/json",
        }

    def default_header_generator(self):
        return {
            'Authorization': f"{self.token_type} {self.access_token}",
            'Accept': "application/json",
            'company': self.okticket_company_id,
        }

    def find(self, path, params=None, https=False, company_in_header=False):
        url = self.get_full_path(path)
        header_gen_method = None if company_in_header else self.find_header_generator
        return self.general_request(url, "GET", {}, header_gen_method=header_gen_method, params=params, https=https)

    def find_one(self, path, params=None, https=False, company_in_header=False):
        return self.find(path, params=params, https=https, company_in_header=company_in_header)

    def general_request(self, url, type_request, fields_dict, headers=None,
                        header_gen_method=None, params=None, raw_response=False, only_data=True, https=False,
                        _attempt=0):
        """Perform a request, recovering from token expiry, rate limiting and
        dropped connections.

        The access token is only valid for 30 minutes, so a long import will
        cross its expiry and get a 401. That re-login used to be dead code:
        ``request_base`` swallowed every exception in a ``finally: return``, so
        the ``except AuthError`` below never fired and the import silently
        stopped returning data. The same applies to the documented per-minute
        call limit (429), which was not handled at all.

        A dropped connection is the third recoverable case, and the one that is
        not an API answer at all: the peer closes without responding, so there
        is no status to interpret.
        """
        try:
            default_header = self.default_header_generator() if not header_gen_method else {}
            headers = headers or (header_gen_method(fields_dict) if header_gen_method else {})
            default_header.update(headers)
            result = self.process_request(
                url, type_request, params=params, data=fields_dict, headers=default_header,
                raw_response=raw_response, only_data=only_data, https=https
            )
        except AuthError:
            # Never retry the token endpoint itself: bad credentials would recurse.
            auth_url = self.base_url + self.auth_uri
            if url == auth_url or _attempt >= MAX_REQUEST_RETRIES:
                raise UserError(_auth_error_message(url))
            _logger.info('Okticket token rejected (401) on %s; re-authenticating '
                         '(attempt %s/%s)', url, _attempt + 1, MAX_REQUEST_RETRIES)
            # Prefer the refresh grant: it is one call and does not re-send the
            # user password. refresh() already degrades to a full login when the
            # refresh token is missing or spent.
            self.refresh(https=https)
            return self.general_request(
                url, type_request, fields_dict, headers=headers,
                header_gen_method=header_gen_method, params=params,
                raw_response=raw_response, only_data=only_data, https=https,
                _attempt=_attempt + 1,
            )
        except RateLimitError as rate_exc:
            if _attempt >= MAX_REQUEST_RETRIES:
                raise UserError(
                    'Okticket call limit per minute exceeded and still failing after '
                    '%s retries on %s. Reduce the import batch size or retry later.'
                    % (MAX_REQUEST_RETRIES, url)
                )
            delay = rate_exc.retry_after or RATE_LIMIT_BACKOFF[
                min(_attempt, len(RATE_LIMIT_BACKOFF) - 1)]
            _logger.warning('Okticket rate limit hit on %s; waiting %ss before retry '
                            '(attempt %s/%s)', url, delay, _attempt + 1, MAX_REQUEST_RETRIES)
            time.sleep(delay)
            return self.general_request(
                url, type_request, fields_dict, headers=headers,
                header_gen_method=header_gen_method, params=params,
                raw_response=raw_response, only_data=only_data, https=https,
                _attempt=_attempt + 1,
            )
        except (http.client.HTTPException, OSError, GatewayError) as transport_exc:
            # Dropped connection, socket timeout or TLS failure. None of the
            # connector exceptions derive from these, so this cannot swallow an
            # API answer -- it only fires when no answer arrived.
            #
            # Without a retry a single blip is permanent and silent: the expense
            # sheet builder catches whatever reaches it and discards the batch,
            # so one "Remote end closed connection without response" left 155
            # already imported expenses with no sheet while the import still
            # reported success.
            #
            # Retried for every verb, not just the idempotent ones. The peer may
            # have processed the request before closing, but OkTicket answers a
            # repeated report name with a 422 that the sheet builder already
            # handles as a warning, so a duplicated write surfaces instead of
            # passing unnoticed. Dropping the record is the worse outcome.
            if _attempt >= MAX_REQUEST_RETRIES:
                raise UserError(
                    'Okticket connection to %s failed after %s retries: %s'
                    % (url, MAX_REQUEST_RETRIES, transport_exc)
                )
            delay = TRANSPORT_BACKOFF[min(_attempt, len(TRANSPORT_BACKOFF) - 1)]
            _logger.warning('Okticket transport error on %s (%s); waiting %ss '
                            'before retry (attempt %s/%s)', url, transport_exc,
                            delay, _attempt + 1, MAX_REQUEST_RETRIES)
            time.sleep(delay)
            return self.general_request(
                url, type_request, fields_dict, headers=headers,
                header_gen_method=header_gen_method, params=params,
                raw_response=raw_response, only_data=only_data, https=https,
                _attempt=_attempt + 1,
            )

        if result and 'result' in result and not result['result'] \
                and 'log' in result and result['log'].get('type') == 'error':
            error_msg = f"Error status {result['log']['status']}: {result['log']['result']}"
            raise UserError(error_msg)

        return result

    def get_http_connection(self, https=False):
        connection_cls = http.client.HTTPSConnection if https else http.client.HTTPConnection
        return connection_cls(self.http_client_conn_url, timeout=REQUEST_TIMEOUT)

    def process_request(self, url, type_request, params=None, data=None, headers=None, raw_response=None,
                        only_data=True, https=False):
        assert self.http_client_conn_url, "http_client_conn_url param is required"

        # Reset per request: a caller that walks pages needs to know whether the
        # listing it got back is the whole thing. See the truncation note below.
        self.last_listing_truncated = False

        if params:  # URL params
            params = urllib.parse.urlencode(params)
            if type_request == "GET" and params:
                # Some paths already carry a query string (e.g. "/reports?with=user"),
                # so the separator cannot be a hardcoded "?".
                url = f"{url}{'&' if '?' in url else '?'}{params}"

        conn = self.get_http_connection(https=https)
        try:
            payload_json = json.dumps(data)
            response = self.request_base(url, type_request, conn, params=params, data=payload_json, headers=headers,
                                         raw_response=raw_response)
            result = response['result']
            # ``result`` is not always a payload: 204 (successful DELETE) and a
            # 404 answered outside the 'Not Found' reason yield a bool, and
            # unwrapping it raised "'bool' object has no attribute 'get'".
            if only_data and isinstance(result, dict):
                page_payload = response['result']
                result = result.get('data')
                page = 1
                while True:
                    next_url = self._get_next_page_url(page_payload, url, page, params)
                    if not next_url:
                        break
                    page += 1
                    conn.close()
                    conn = self.get_http_connection(https=https)
                    response = self.request_base(next_url, type_request, conn, params=params, data=payload_json,
                                                 headers=headers, raw_response=raw_response)
                    page_payload = response['result']
                    page_data = page_payload.get('data') if isinstance(page_payload, dict) else None
                    if not page_data:
                        # The walk stops here, but there are two very different
                        # reasons to stop and the caller has to tell them apart.
                        # A page that answered with an error leaves ``result`` at
                        # False (request_base logs the error and returns rather
                        # than raising for anything but 401/429/gateway), so a
                        # 500 in the middle of a listing used to look exactly
                        # like reaching the end: the partial list was returned,
                        # nobody noticed, and the expense importer went on to
                        # advance its "import since" watermark past records it
                        # had never fetched -- which drops them out of the
                        # incremental window for good. Measured against the demo
                        # company: 640 records returned instead of 642, no
                        # exception raised.
                        self.last_listing_truncated = not isinstance(page_payload, dict)
                        if self.last_listing_truncated:
                            _logger.error(
                                'Okticket listing truncated at page %s of %s: the page '
                                'answered with an error, so the result is incomplete',
                                page, next_url)
                        break
                    result += page_data
        finally:
            conn.close()
        return {'result': result, 'log': response['log']}

    def _get_next_page_url(self, payload, first_page_url, current_page, params=None):
        """Resolve the URL of the next page of results, or None when finished.

        The API returns both ``links`` (first/last/prev/next) and ``meta``
        (current_page/last_page/per_page/total). ``links.next`` is preferred, but
        it comes as a bare "?page=N" and drops the original search parameters, so
        they must be re-appended or every page after the first would come back
        unfiltered. ``meta`` is the documented mechanism and is used as a
        fallback in case ``links`` is absent.
        """
        if not isinstance(payload, dict):
            return None
        links_next = (payload.get('links') or {}).get('next')
        if links_next:
            if params:
                separator = '&' if '?' in links_next else '?'
                return f"{links_next}{separator}{params}"
            return links_next
        meta = payload.get('meta') or {}
        try:
            current = int(meta.get('current_page') or current_page)
            last = int(meta.get('last_page') or 0)
        except (TypeError, ValueError):
            return None
        if not last or current >= last:
            return None
        separator = '&' if '?' in first_page_url else '?'
        return f"{first_page_url}{separator}page={current + 1}"

    def request_base(self, url, type_request, conn, params={}, data={}, headers={}, raw_response=None):
        """ Log.event structure """
        log = {
            'tag': type_request,
            'headers': headers,
            'url': url,
            'data': data,
            'status': False,
            'result': False,
        }
        result = False
        log_result = False
        conn.request(type_request, url, data, headers)
        response = conn.getresponse()
        status = response.status
        try:
            if status in (200, 201):
                data = response.read()
                if raw_response:
                    result = data.decode("utf-8")
                else:
                    try:
                        if type(data) == bytes:
                            data = data.decode('UTF-8')
                        result = json.loads(data)
                    except (ValueError, TypeError):
                        raise JSONDecodeError(response)
            elif status == 204:
                # 204 No Content is the documented *success* response for DELETE.
                # It used to be logged as an error, reporting a correct deletion
                # as a failure.
                _logger.info("Okticket DELETE completed (204 No Content)")
                result = True
            elif status == 401:
                raise AuthError
            elif status == 403:
                raise ForbiddenError
            elif status == 404:
                if response.reason == 'Not Found':
                    # Documented as "log a warning and continue". Raising here
                    # was pointless: ResourceNotFoundError is a
                    # BaseOkticketError, so the handler below swallowed it and
                    # the method returned ``result = True`` anyway -- and then
                    # process_request did True.get('data') and blew up with
                    # "'bool' object has no attribute 'get'". An empty, well
                    # formed payload is what the callers can actually work with.
                    _logger.warning("Okticket object not found (404); operations will continue")
                    result = {'data': [], 'links': {}, 'meta': {}}
                    log['type'] = 'warning'
                else:
                    raise ResourceNotFoundError
            elif status == 409:
                raise ConflictError
            elif status == 412:
                # ``self.impersonate`` was referenced here but never defined on the
                # connector, so a 412 raised AttributeError instead of this error.
                raise ImpersonateError
            elif status == 413:
                raise RequestEntityTooLargeError
            elif status == 422:
                # http.client responses have no .json(); the body has to be read
                # and parsed. Documented shape: {"message": ..., "errors": {...}}.
                raise ValidationError(self._read_error_message(response))
            elif status == 429:
                raise RateLimitError(retry_after=_parse_retry_after(response))
            elif status == 500:
                raise ServerError
            elif status in (502, 503, 504):
                # Gateway errors come from the front end, not from the API, and
                # clear on their own. Handled like a dropped connection.
                raise GatewayError(status)
            else:
                raise UnknownError(status)

            log_result = result

        except (AuthError, RateLimitError, GatewayError):
            # These three must reach general_request so it can re-authenticate,
            # back off or retry the gateway error. The previous `finally: return` suppressed every exception,
            # which is why the 401 re-login and any rate-limit recovery never ran.
            log['type'] = 'error'
            raise
        except BaseOkticketError as conExc:
            # Does not downgrade a type already set to 'warning' (the 404 case):
            # a not-found is not an error and must not be reported as one.
            if log.get('type') != 'warning':
                log['type'] = 'error'
            log_result = str(conExc)

        finally:
            # Updates log info
            log.update({
                'status': status,
                'result': log_result, })

        return {
            'result': result,
            'log': log,
        }

    def _read_error_message(self, response):
        """Extract a readable message from an error response body."""
        try:
            body = response.read()
            if isinstance(body, bytes):
                body = body.decode('UTF-8', errors='replace')
            payload = json.loads(body)
        except Exception:
            return 'The given data was invalid'
        if not isinstance(payload, dict):
            return str(payload)
        message = payload.get('message') or 'The given data was invalid'
        errors = payload.get('errors')
        if isinstance(errors, dict):
            detail = '; '.join(
                '%s: %s' % (field, ', '.join(msgs) if isinstance(msgs, list) else msgs)
                for field, msgs in errors.items()
            )
            if detail:
                return '%s (%s)' % (message, detail)
        return message
