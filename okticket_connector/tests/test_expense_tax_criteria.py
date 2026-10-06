# Copyright 2026 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestExpenseTaxCriteria(TransactionCase):
    """An expense synchronised from OkTicket never carries VAT.

    Spanish law only lets input VAT be deducted against an invoice (LIVA
    art. 97), and Odoo books whatever tax an expense carries as deductible: a
    472 line and boxes [28]/[29] of the 303 on an entry the SII never sees. So
    neither the receipt's breakdown nor the product's supplier taxes may reach
    the expense. The breakdown stays in ``okticket_response``, for the supplier
    invoice to read.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.backend = cls.env["okticket.backend"].create(
            {
                "name": "Backend de prueba",
                "location": "https://example.invalid/v2/public",
                "version": "1.0",
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
        cls.tax_21 = cls.env["account.tax"].create(
            {
                "name": "OKT CRIT 21%",
                "amount": 21.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": cls.company.id,
            }
        )
        # A product that does carry a supplier tax: that is the trap, since
        # Odoo computes the expense's taxes from it.
        cls.product = cls.env["product.product"].create(
            {
                "name": "Restaurante de prueba",
                "can_be_expensed": True,
                "okticket_type_prod_id": 777,
                "supplier_taxes_id": [(6, 0, cls.tax_21.ids)],
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Empleada de prueba"})
        cls.receipt = {"_id": "okt-1", "type_id": 777, "amount": 121.0,
                       "taxes": [{"p": 21, "b": 100.0}]}

    def _mapped(self, record):
        with self.backend.work_on("okticket.hr.expense") as work:
            return work.component(usage="importer").product_id(record)

    def _expense(self, **values):
        vals = {
            "name": "Ticket",
            "employee_id": self.employee.id,
            "product_id": self.product.id,
            "total_amount_currency": 121.0,
        }
        vals.update(values)
        return self.env["hr.expense"].create(vals)

    # ------------------------------------------------------------------
    def test_the_mapping_clears_the_taxes(self):
        """A reported 21% does not become a tax on the expense."""
        values = self._mapped(self.receipt)
        self.assertEqual(values["product_id"], self.product.id)
        self.assertEqual(values["tax_ids"], [Command.clear()])

    def test_an_imported_expense_ignores_the_product_taxes(self):
        expense = self._expense(
            okticket_response=json.dumps(self.receipt),
            **{k: v for k, v in self._mapped(self.receipt).items()
               if k != "product_id"},
        )
        self.assertFalse(expense.tax_ids)
        self.assertEqual(expense.tax_amount_currency, 0.0)
        self.assertEqual(expense.untaxed_amount_currency, 121.0)

    def test_even_without_the_mapping_values(self):
        """Odoo's own compute must not put them back either."""
        expense = self._expense(okticket_response=json.dumps(self.receipt))
        self.assertFalse(expense.tax_ids)

    def test_changing_the_product_does_not_bring_them_back(self):
        expense = self._expense(okticket_response=json.dumps(self.receipt))
        other = self.product.copy({"name": "Otro producto"})
        expense.product_id = other
        self.assertFalse(expense.tax_ids)

    def test_an_expense_typed_in_odoo_keeps_the_native_behaviour(self):
        """Only what OkTicket synchronises is affected."""
        self.assertEqual(self._expense().tax_ids, self.tax_21)


@tagged("post_install", "-at_install")
class TestBackendWorkLanguage(TransactionCase):
    """The language a scheduled run writes in cannot depend on who started it.

    Odoo's "Run manually" button calls ``with_context({'lastcall': ...})``,
    which replaces the context instead of extending it, so the job loses the
    language and every translated string it writes comes out in English: the
    log entries, the reason left on an expense and the name of the expense
    sheet, which then travels to OkTicket as the report name.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.backend = cls.env["okticket.backend"].create(
            {
                "name": "Backend de idioma",
                "location": "https://example.invalid/v2/public",
                "version": "1.0",
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

    def _sin_idioma(self):
        """The backend as the manual trigger leaves it: no lang in context."""
        backend = self.backend.with_context({})
        self.assertFalse(backend.env.context.get("lang"))
        return backend

    def test_the_backend_states_the_language(self):
        spanish = self.env["res.lang"]._activate_lang("es_ES")
        self.backend.default_lang_id = spanish
        backend = self._sin_idioma()
        self.assertEqual(backend.okticket_work_lang(), "es_ES")
        self.assertEqual(backend.okticket_work_env().env.context.get("lang"), "es_ES")

    def test_without_one_it_falls_back_to_the_company(self):
        self.backend.default_lang_id = False
        self.env["res.lang"]._activate_lang("es_ES")
        self.company.partner_id.lang = "es_ES"
        self.assertEqual(self._sin_idioma().okticket_work_lang(), "es_ES")

    def test_the_work_env_also_carries_the_company(self):
        backend = self.backend.okticket_work_env()
        self.assertEqual(backend.env.company, self.company)
