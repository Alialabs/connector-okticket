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

from .base_connector import BaseConnector


class OkTicketOpenConnector(BaseConnector):

    def __init__(self, params={}):
        self.http_client_conn_url = params.get('http_client_conn_url')
        self.base_url = params.get('base_url')
        self.auth_uri = params.get('auth_uri')
        self.uri_op_path = params.get('uri_op_path')
        self.api_login = params.get('api_login')
        self.api_password = params.get('api_password')
        self.grant_type = params.get('grant_type')
        self.oauth_client_id = params.get('oauth_client_id')
        self.oauth_secret = params.get('oauth_secret')
        self.scope = params.get('scope')
        self.okticket_company_id = params.get('okticket_company_id')
        self.https = params.get('https')

        self.token_type = ""
        self.access_token = ""
        self.refresh_token = ""

        # print('INICIALIZAMOS OkTicket connector...')


    def auth_test(self, https=False):
        return self.login(https=https)

    def get_login_values(self):
        return {
            'grant_type': self.grant_type,
            'client_id': self.oauth_client_id,
            'client_secret': self.oauth_secret,
            'username': self.api_login,
            'password': self.api_password,
            'scope': self.scope,
        }

    def get_login_params(self):
        return {'grant_type': self.grant_type, 'scope': self.scope}

    def find_expenses(self, params=False, https=False): # TODO: donde situar los params pasarlos aqui o de atras??
        path = "/expenses"
        return self.find(path, params=params, https=https, company_in_header=True)

    def find_expense_by_id(self, id, https=False):
        path = "/expenses/{0}".format(id)
        params = {
            'with': 'report', # TODO: como indicar que quiero o no este parametro activo?
        }
        return self.find_one(path, params=params, https=https)

    def find_report_by_id(self, id, https=False):
        path = "/reports/{0}".format(id)
        return self.find_one(path, params={}, https=https, company_in_header=True)

    def find_users(self, params=False, https=False):
        path = "/users"
        return self.find(path, params=params, https=https, company_in_header=True)

    def find_products(self, params=False, https=False):
        path = "/categories"
        return self.find(path, params=params, https=https, company_in_header=True)

    def find_expense_sheets(self, params=False, https=False):
        path = "/reports?with=user,expenses"
        return self.find(path, params=params, https=https, company_in_header=True)

    def autocomplete_relational_fields(self, data):
        '''
        Identifica campos claves en los diccionarios de valores recuperados y recupera la informacion
        especifica de cada uno de esos objetos a partir del id que trae.
        :param data: dict valores recuperados de request previa
        :return:
        '''
        # TODO: diccionario simulacion clave-valor de fichero de campos 'especiales' para recuperar
        test = {'report_id': self.find_report_by_id,}
        # TODO Loxo: si usamos report_id sustituye 'report_id' por diccionario de valores pero si se incluyen
        # los parametros 'with=report' se anade el campo 'report' con esta informacion y no seria necesario
        # este autocompletado, si no apareceria la misma informacion en 'report' y 'report_id'

        temporal_result = {}
        for key, val_id in data.items():
            if test.has_key(key):
                find_method = test[key]
                temporal_result[key] = find_method(val_id)
        data.update(temporal_result) # Merge de datos originales con los nuevos recuperados
        return data


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: