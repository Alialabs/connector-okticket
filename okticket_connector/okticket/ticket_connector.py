# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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

    def find_expenses(self, params=False, https=False):
        path = "/expenses"
        return self.find(path, params=params, https=https, company_in_header=True)

    def find_expense_by_id(self, id, https=False):
        path = "/expenses/{0}".format(id)
        params = {
            'with': 'report',
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

    def find_cost_center(self, params=False, https=False):
        path = "/cost-centers"
        return self.find(path, params=params, https=https, company_in_header=True)

    def autocomplete_relational_fields(self, data):
        """
        Identifies key fields in obtained dicts and gets the specific information
        of every object based on the obtained id
        :param data: obtained values dictionary from previous request
        """
        aux = {'report_id': self.find_report_by_id, }
        # If we use 'report_id' it overwrites 'report_id' by dictionary.
        # If 'with=report' params are included, 'report' field is added with this data and autocomplete
        # is no needed or the same data will be in 'report' and 'report_id'
        temporal_result = {}
        for key, val_id in data.items():
            if key in aux:
                find_method = aux[key]
                temporal_result[key] = find_method(val_id)
        data.update(temporal_result)
        return data
