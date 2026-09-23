# Copyright 2026 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestExpenseTaxCriteria(TransactionCase):
    """What the importer does with the rates OkTicket reports.

    The rule the customer settled on: the connector never invents a rate. A
    receipt that declares nothing, that declares several, or that declares one
    its category does not admit comes in with no tax and a warning in the
    connector log, because a tax nobody reported is indistinguishable from a
    correct one once it is on the expense.
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
        cls.tax_10 = cls._tax("OKT CRIT 10%", 10.0)
        cls.tax_21 = cls._tax("OKT CRIT 21%", 21.0)
        cls.product = cls.env["product.template"].create(
            {
                "name": "Taxi de prueba",
                "can_be_expensed": True,
                "supplier_taxes_id": [(6, 0, cls.tax_21.ids)],
            }
        )

    @classmethod
    def _tax(cls, name, amount):
        return cls.env["account.tax"].create(
            {
                "name": name,
                "amount": amount,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": cls.company.id,
            }
        )

    def _map(self, rate, tax):
        return self.env["okticket.product.tax.mapping"].create(
            {
                "product_tmpl_id": self.product.id,
                "company_id": self.company.id,
                "okticket_rate": rate,
                "tax_id": tax.id,
            }
        )

    def _resolve(self, taxes):
        """What the importer would put on an expense reporting ``taxes``."""
        variant = self.product.product_variant_id
        with self.backend.work_on("okticket.hr.expense") as work:
            component = work.component(usage="importer")
            return component._resolve_record_taxes(
                {"_id": "test", "taxes": taxes}, self.company.id, variant
            )

    def _warnings(self):
        return self.env["log.event"].search_count(
            [("backend_id", "=", self.backend.id), ("type", "=", "warning")]
        )

    # ------------------------------------------------------------------
    def test_a_declared_rate_uses_the_declared_tax(self):
        self._map(10.0, self.tax_10)
        self.assertEqual(self._resolve([{"p": 10, "b": 90.0}]), self.tax_10.ids)

    def test_no_breakdown_means_no_tax(self):
        """Not the product default: nobody read a rate on that receipt."""
        self.assertEqual(self._resolve([]), [])
        self.assertEqual(self._resolve([{"p": 21, "b": 0}]), [])

    def test_several_rates_mean_no_tax_and_a_warning(self):
        """An expense holds one base, so keeping one of the rates is a guess."""
        before = self._warnings()
        self.assertEqual(
            self._resolve([{"p": 10, "b": 50.0}, {"p": 21, "b": 30.0}]), []
        )
        self.assertEqual(self._warnings(), before + 1)

    def test_a_rate_the_category_does_not_admit_means_no_tax(self):
        """The receipt contradicts its own category: a capture error, usually.

        It must not fall back to the product's default tax, which is what made
        a 5% car park come in at 21%.
        """
        self._map(10.0, self.tax_10)
        before = self._warnings()
        self.assertEqual(self._resolve([{"p": 21, "b": 80.0}]), [])
        self.assertEqual(self._warnings(), before + 1)

    def test_a_rate_the_chart_has_no_tax_for_means_no_tax(self):
        before = self._warnings()
        self.assertEqual(self._resolve([{"p": 5, "b": 80.0}]), [])
        self.assertEqual(self._warnings(), before + 1)

    def test_a_product_that_declares_nothing_keeps_the_old_behaviour(self):
        """A customer's own category is not second-guessed.

        Without a single declared row there is no criterion to contradict, so
        the resolution chain still reaches the tax the product carries.
        """
        self.assertEqual(self._resolve([{"p": 21, "b": 80.0}]), self.tax_21.ids)

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
