# -*- coding: utf-8 -*-
#
#    Created on 8/04/19
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

import http.client, urllib.parse
import json
import logging
_logger = logging.getLogger(__name__)

from .exceptions import (
    BaseOkticketError,
    AuthError,
    ConflictError,
    ImpersonateError,
    ServerError,
    ValidationError,
    ResourceNotFoundError,
    RequestEntityTooLargeError,
    UnknownError,
    ForbiddenError,
    JSONDecodeError
)


class BaseConnector(object):

    # Atributos
    http_client_conn_url =  None
    base_url = None
    auth_uri = None
    uri_op_path = None
    token_type = None
    access_token = None
    refresh_token = None
    okticket_company_id = None
    backend_id = None
    https = False

    def __init__(self):
        self.http_client_conn_url = ""
        self.base_url = ""
        self.auth_uri = ""
        self.uri_op_path = ""
        self.token_type = ""
        self.access_token = ""
        self.refresh_token = ""
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

    def login(self, https=False):
        '''
        Login de usuario. Almacena token_type y access_token recuperados.
        :return:
        '''
        fields_dict = self.get_login_values()
        response = self.general_request(self.base_url + self.auth_uri, "POST", fields_dict,
                                header_gen_method=self.login_header_generator, only_data=False, https=https)
        if response and response.get('result'):
            self.token_type = response['result'].get('token_type')
            self.access_token = response['result'].get('access_token')
        return response

    def get_full_path(self, path):
        return self.base_url + self.uri_op_path + path

    def find_header_generator(self, params):
        result = {
            'Authorization': self.token_type + ' ' + self.access_token,
            'Accept': "application/json",
        }
        return result

    def default_header_generator(self):
        '''Genera un header template'''
        return {
            'Authorization': self.token_type + ' ' + self.access_token,
            'Accept': "application/json",
            'company': self.okticket_company_id,
        }

    def find(self, path, params=None, https=False, company_in_header=False):
        '''
        Peticiones GET para recuperacion lista de elementos.
        :param path: path especifico de un objeto
        :param params: parametros de filtrado de la peticion
        :return: [ dict ]
        '''
        url = self.get_full_path(path)
        headers = {}
        if company_in_header:
            header_gen_method = False
        else:
            header_gen_method = self.find_header_generator

        response = self.general_request(url, "GET", fields_dict={}, headers=headers,
                                                header_gen_method=header_gen_method,
                                                params=params, https=https)
        # TODO: controlar numero de elementos por recuperar y realizar peticiones hasta recuperarlos todos
        return response

    def find_one(self, path, params=None, https=False, company_in_header=False):
        url = self.get_full_path(path)
        headers = {}
        if company_in_header:
            header_gen_method = False
        else:
            header_gen_method = self.find_header_generator
        response = self.general_request(url, "GET", fields_dict={}, headers=headers,
                                        header_gen_method=header_gen_method,
                                        params=params, https=https)
        return response

    def general_request(self, url, type_request, fields_dict, headers=None,
                header_gen_method=None, params=None, raw_response=False, only_data=True, https=False):
        try:
            # Generacion dinamica de headers y params
            default_header = {}
            if not header_gen_method:
                default_header = self.default_header_generator()
            headers = headers or header_gen_method and header_gen_method(fields_dict) or {}
            default_header.update(headers)
            # if url != 'http://dev.okticket.es/api/public/oauth/token':
            #     headers['company'] = '12902'
            result = self.process_request(url, type_request, params=params, data=fields_dict, headers=default_header,
                                          raw_response=raw_response, only_data=only_data, https=https)
        except AuthError:
            # Reintento tras nueva autenticacion
            if url != 'http://dev.okticket.es/api/public/oauth/token':
                self.login(https=https)
                result = self.general_request(url, type_request, fields_dict, headers=headers,
                                              header_gen_method=header_gen_method, params=params,
                                              raw_response=raw_response, only_data=only_data, https=https)
        return result

    def get_http_connection(self, https=False):
        if https:
            conn = http.client.HTTPSConnection(self.http_client_conn_url)
        else:
            conn = http.client.HTTPConnection(self.http_client_conn_url)
        return conn

    def process_request(self, url, type_request, params=None, data=None, headers=None, raw_response=None, only_data=True, https=False):
        '''
        Procesa la peticion HTTP
        '''
        assert self.http_client_conn_url, "http_client_conn_url param is required"

        # Incluir parametros en url de la peticion
        if params:
            params = urllib.parse.urlencode(params)
            url = url + "?" + params if type_request == "GET" and params else url

        conn = self.get_http_connection(https=https)
        try:
            payload_json = json.dumps(data) # codificacion en JSON
            response = self.request_base(url, type_request, conn, params=params, data=payload_json, headers=headers, raw_response=raw_response)
            result = response['result']
            if only_data:
                result = result.get('data')
                # Itera entre todas las posibles paginas de listado de elementos
                if response['result'].get('links'): # TODO: REVISAR EN PRODUCCIÓN
                    while response['result']['links'].get('next'):
                        # Cerrar y abrir de nuevo la conexión para realizar la petición a la siguiente "página"
                        conn.close()
                        conn = self.get_http_connection(https=https)

                        next_url = response['result']['links']['next']
                        next_url = next_url + "&" + params if type_request == "GET" and params else next_url
                        response = self.request_base(next_url, type_request, conn, params=params, data=data, headers=headers,
                                                     raw_response=raw_response)
                        result = result + response['result'].get('data')
        finally:
            conn.close()
        return {
            'result': result,
            'log': response['log'],
        }

    def request_base(self, url, type_request, conn, params={}, data={}, headers={}, raw_response=None):
        # Definicion estructura de diccionario de valores para log.event
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
        try:
            if response.status in (200, 201):
                data = response.read()
                if raw_response:
                    result = data.decode("utf-8")
                else:
                    try:
                        result = json.loads(data)
                    except (ValueError, TypeError):
                        raise JSONDecodeError(response)
            elif response.status == 401:
                raise AuthError
            elif response.status == 403:
                raise ForbiddenError
            elif response.status == 404:
                if response.reason == 'Not Found':
                    _logger.warning(
                        "Not fount object!!! Operations will continue...")
                    # TODO: no encuentra el objeto con el id indicado en OKTICKET
                    result = True
                raise ResourceNotFoundError
            elif response.status == 409:
                raise ConflictError
            elif response.status == 412 and self.impersonate is not None:
                raise ImpersonateError
            elif response.status == 413:
                raise RequestEntityTooLargeError
            elif response.status == 422:
                errors = response.json()['errors']
                raise ValidationError(map(str, (', '.join(e if e else ': '.join(e) for e in errors))))
            elif response.status == 500:
                raise ServerError
            elif response.status == 204:
                _logger.warning("DELETE done...")  # TODO: no encuentra el objeto con el id indicado en OKTICKET
                result = True
            else:
                raise UnknownError(response.status)

            response = response.status
            log_result = result

        except BaseOkticketError as conExc:
            response = response.status
            log['type'] = 'error'
            log_result = str(conExc)

        finally:
            # Actualizar info de log
            log.update({
                'status': response,
                'result': log_result,})
            return {
                'result': result,
                'log': log,
            }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: