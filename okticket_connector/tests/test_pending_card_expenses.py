# Copyright 2026 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from unittest.mock import MagicMock

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPendingCardExpenses(TransactionCase):
    """Card movements with no receipt yet (OkTicket status 4) are opt-in.

    OkTicket creates an expense for every OkTicket card payment, in status 4,
    with no category, no image and no report. It moves to status 1 -- same
    ``_id`` -- once the employee uploads the receipt. The connector skips them
    unless the company asks for them, and then gives them a default product.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.backend = cls.env["okticket.backend"].create(
            {
                "name": "Backend de pendientes",
                "http_client_conn_url": "example.invalid",
                "base_url": "https://example.invalid/v2/public",
                "image_base_url": "https://example.invalid/v2/public",
                "auth_uri": "/oauth/token",
                "uri_op_path": "/api",
                "api_login": "test",
                "api_password": "test",
                "oauth_client_id": "1",
                "oauth_secret": "test",
                "grant_type": "password",
                "scope": "*",
                "company_id": cls.company.id,
            }
        )
        # Any expense account of the company will do: the point is that the
        # pending movement takes the account of the default product.
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"),
             ("company_ids", "in", cls.company.ids)], limit=1
        )
        cls.default_product = cls.env["product.product"].create(
            {
                "name": "Movimiento de tarjeta sin ticket",
                "can_be_expensed": True,
                "property_account_expense_id": cls.expense_account.id,
            }
        )
        cls.restaurant = cls.env["product.product"].create(
            {
                "name": "Restaurante",
                "can_be_expensed": True,
                # A type of its own, not 0/1, so the lookup goes by type alone:
                # with okticket_connector_product_synchronization installed
                # the category id is computed from bindings and cannot be set.
                "okticket_type_prod_id": 777,
            }
        )
        # As OkTicket sends a card movement before the receipt is uploaded.
        cls.pending = {
            "_id": "okt-card-1",
            "status_id": 4,
            "source": "SOURCE_OKT_CARD",
            "payment_method": "tarjeta",
            "amount": 1.4,
            "comments": "HOTEL PLAYA SOL ES PITLARI",
            "custom_fields": {},
        }

    def _enable(self, product=True):
        self.company.okticket_import_pending_expenses = True
        self.company.okticket_pending_expense_product_id = (
            self.default_product if product else False
        )

    def _importer(self, work):
        return work.component(usage="importer")

    def _mapped(self, record):
        with self.backend.work_on("okticket.hr.expense") as work:
            importer = self._importer(work)
            values = importer.product_id(record) or {}
            values.update(importer.account_id(record) or {})
            values.update(importer.okticket_status(record) or {})
            return values

    def _statuses_asked(self):
        with self.backend.work_on("okticket.hr.expense") as work:
            adapter = work.component(usage="backend.adapter")
            adapter._auth = lambda force=False: True
            adapter.okticket_api = MagicMock()
            adapter.okticket_api.find_expenses.return_value = {
                "result": [], "log": {"msg": "GET /expenses"},
            }
            adapter.search()
            params = adapter.okticket_api.find_expenses.call_args.kwargs["params"]
            return params["statuses"]

    # ------------------------------------------------------------------
    def test_off_by_default(self):
        self.assertFalse(self.env["res.company"].new({}).okticket_import_pending_expenses)

    def test_off_asks_for_the_same_statuses_as_before(self):
        self.assertEqual(self._statuses_asked(), "0,1,2")

    def test_on_also_asks_for_status_4(self):
        self._enable()
        self.assertEqual(self._statuses_asked(), "0,1,2,4")

    def test_off_a_pending_movement_gets_no_product(self):
        self.assertNotIn("product_id", self._mapped(self.pending))

    def test_on_a_pending_movement_gets_the_default_product(self):
        self._enable()
        values = self._mapped(self.pending)
        self.assertEqual(values["product_id"], self.default_product.id)
        self.assertEqual(values["account_id"], self.expense_account.id)
        self.assertEqual(values["okticket_status"], "pending")

    def test_on_without_product_it_is_still_skipped(self):
        self._enable(product=False)
        self.assertNotIn("product_id", self._mapped(self.pending))

    def test_on_a_confirmed_expense_with_no_category_is_not_rescued(self):
        """The default product is only for card movements, not for broken data."""
        self._enable()
        record = dict(self.pending, status_id=1, type_id=99, category_id=99)
        self.assertNotIn("product_id", self._mapped(record))

    def test_once_the_receipt_arrives_the_real_category_wins(self):
        self._enable()
        record = dict(self.pending, status_id=1, type_id=777)
        values = self._mapped(record)
        self.assertEqual(values["product_id"], self.restaurant.id)
        self.assertEqual(values["okticket_status"], "confirmed")

    def test_a_pending_movement_with_a_category_keeps_it(self):
        self._enable()
        record = dict(self.pending, type_id=777)
        self.assertEqual(self._mapped(record)["product_id"], self.restaurant.id)
