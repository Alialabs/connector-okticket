# Copyright 2026 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.okticket_connector_cost_center.models.okticket_analytic_account import (
    AccountAnalyticAccountAdapter,
)


@tagged('post_install', '-at_install')
class TestCostCenterGlobal(TransactionCase):
    """The company decides whether new cost centers are global in OkTicket."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Not automatic: the test creates the cost center itself.
        cls.company.create_cost_center_automatically = False
        # One backend per company: reuse the database's own when there is one.
        Backend = cls.env['okticket.backend'].with_context(active_test=False)
        cls.backend = Backend.search([('company_id', '=', cls.company.id)], limit=1)
        if not cls.backend:
            cls.backend = Backend.create({
                'name': 'Backend de centros de coste',
                'http_client_conn_url': 'example.invalid',
                'base_url': 'https://example.invalid/v2/public',
                'image_base_url': 'https://example.invalid/v2/public',
                'auth_uri': '/oauth/token',
                'uri_op_path': '/api',
                'api_login': 'test',
                'api_password': 'test',
                'oauth_client_id': '1',
                'oauth_secret': 'test',
                'grant_type': 'password',
                'scope': '*',
                'company_id': cls.company.id,
            })
        cls.backend.active = True
        plan_vals = {'name': 'Plan de centros de coste'}
        if 'company_id' in cls.env['account.analytic.plan']._fields:
            plan_vals['company_id'] = False  # 16.0: a company plan rejects company-less accounts
        cls.plan = cls.env['account.analytic.plan'].create(plan_vals)

    def setUp(self):
        super().setUp()
        self.sent = []
        sent = self.sent

        def fake_create(adapter, values):
            sent.append(values)
            return {'data': {'id': 990000 + len(sent)}}

        one = patch.object(AccountAnalyticAccountAdapter, 'create_cost_center', fake_create)
        one.start()
        self.addCleanup(one.stop)

    def _create_cost_center(self, name, company=True):
        account = self.env['account.analytic.account'].create({
            'name': name,
            'plan_id': self.plan.id,
            'company_id': self.company.id if company else False,
        })
        account._okticket_create()
        return account

    def test_global_by_default(self):
        """Existing installations keep creating global cost centers."""
        self.assertTrue(self.company.okticket_cost_center_global)
        self._create_cost_center('Centro global')
        self.assertIs(self.sent[-1]['global'], True)

    def test_not_global_when_the_company_says_so(self):
        self.company.okticket_cost_center_global = False
        account = self._create_cost_center('Centro no global')
        self.assertIs(self.sent[-1]['global'], False)
        self.assertTrue(account.okticket_bind_ids, 'the cost center is still bound')

    def test_an_account_without_company_uses_the_current_one(self):
        """Project accounts have no company in a single-company database.

        The backend, the OkTicket company and the global option all come from
        the current company then; it used to find no backend and do nothing.
        """
        self.company.okticket_cost_center_global = False
        account = self._create_cost_center('Centro sin compania', company=False)
        self.assertFalse(account.company_id)
        self.assertTrue(account.okticket_bind_ids, 'the cost center was created and bound')
        self.assertEqual(self.sent[-1]['company_id'], self.company.okticket_company_id)
        self.assertIs(self.sent[-1]['global'], False)
