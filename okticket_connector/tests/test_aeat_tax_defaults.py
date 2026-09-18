# Copyright 2026 Alia Technologies, S.L. - http://www.alialabs.com
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

from odoo.tests.common import TransactionCase

from ..models.aeat_tax_defaults import (
    BASE_TAX_BY_RATE_SCOPE,
    OKTICKET_DEFAULT_CATEGORIES,
    category_tax_rows,
    resolve_category,
)


class TestAeatTaxDefaultsTable(TransactionCase):
    """The table itself: identification and coherence, no database involved."""

    def test_identified_by_id_and_name(self):
        resolved = resolve_category(4304, 'Taxi')
        self.assertIsNotNone(resolved)
        category_id, entry, exact = resolved
        self.assertEqual(category_id, 4304)
        self.assertEqual(entry['name'], 'Taxi')
        self.assertTrue(exact)

    def test_identified_by_name_when_the_id_changed(self):
        """A renumbering on OkTicket's side must not lose the criteria."""
        resolved = resolve_category(98765, 'Gasolina')
        self.assertIsNotNone(resolved)
        category_id, entry, exact = resolved
        self.assertEqual(category_id, 6)
        self.assertEqual(entry['nature'], 'consu')
        self.assertFalse(exact, 'the caller has to know the id did not match')

    def test_a_matching_id_alone_is_not_enough(self):
        """The half of the evidence that was assumed to drift cannot decide.

        Applying the criteria of "Taxi" to a category that is called something
        else would put a wrong tax on every expense of it, which is worse than
        putting none.
        """
        self.assertIsNone(resolve_category(4304, 'Material de oficina'))

    def test_name_comparison_ignores_case_and_accents(self):
        self.assertIsNotNone(resolve_category(1, 'RESTAURACION'))
        self.assertIsNotNone(resolve_category(1, ' restauración '))

    def test_unknown_category_is_not_resolved(self):
        self.assertIsNone(resolve_category(29958, 'Catering'))
        self.assertIsNone(resolve_category(None, None))

    def test_catch_all_category_proposes_nothing(self):
        self.assertEqual(category_tax_rows(0), [])

    def test_fuel_is_the_only_goods_category(self):
        goods = [c['name'] for c in OKTICKET_DEFAULT_CATEGORIES.values()
                 if c['nature'] == 'consu']
        self.assertEqual(goods, ['Gasolina'])
        self.assertTrue(all(suffix.endswith('_bc')
                            for _rate, _scope, suffix in category_tax_rows(6)))

    def test_every_row_resolves_to_a_tax_suffix(self):
        """No category may declare a (rate, scope) pair the chart table lacks."""
        for category_id, entry in OKTICKET_DEFAULT_CATEGORIES.items():
            overrides = entry.get('overrides') or {}
            for rate, scope in entry['rates'].items():
                self.assertTrue(
                    overrides.get(rate) or BASE_TAX_BY_RATE_SCOPE.get((rate, scope)),
                    'category %s has no tax for %s%% as %s' % (
                        entry['name'], rate, scope))
            self.assertEqual(len(category_tax_rows(category_id)),
                             len(entry['rates']))

    def test_zero_rate_tells_exempt_from_not_subject(self):
        """Art. 22.Trece does not reach the railway; the leg abroad is not subject."""
        plane = dict((rate, suffix) for rate, _s, suffix in category_tax_rows(4306))
        train = dict((rate, suffix) for rate, _s, suffix in category_tax_rows(4305))
        self.assertEqual(plane[0.0], 'p_iva0_s_sc')
        self.assertEqual(train[0.0], 'p_iva0_ns')


class TestAeatTaxDefaultsApply(TransactionCase):
    """Writing the proposal on a product.

    The taxes come from the Spanish chart when the test database carries one
    and are built here when it does not, so the test exercises the connector's
    behaviour either way instead of depending on l10n_es being installed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.tax_10_s = cls._build_tax('OKT TEST 10% S', 10.0, 'service', 'p_iva10_sc')
        cls.tax_21_g = cls._build_tax('OKT TEST 21% G', 21.0, 'consu', 'p_iva21_bc')
        cls.tax_10_g = cls._build_tax('OKT TEST 10% G', 10.0, 'consu', 'p_iva10_bc')
        cls.other_tax = cls.env['account.tax'].create({
            'name': 'OKT TEST something else 10%',
            'amount': 10.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'company_id': cls.company.id,
        })
        cls.product = cls.env['product.template'].create({
            'name': 'Taxi',
            'can_be_expensed': True,
        })

    @classmethod
    def _build_tax(cls, name, amount, scope, suffix):
        existing = cls.env['product.template']._okticket_chart_tax(
            cls.company, suffix)
        if existing:
            return existing
        tax = cls.env['account.tax'].create({
            'name': name,
            'amount': amount,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'tax_scope': scope,
            'company_id': cls.company.id,
        })
        cls.env['ir.model.data'].create({
            'module': 'account',
            'name': '%s_account_tax_template_%s' % (cls.company.id, suffix),
            'model': 'account.tax',
            'res_id': tax.id,
        })
        return tax

    def _apply(self, external_id=4304, name='Taxi'):
        return self.product.okticket_apply_aeat_tax_defaults(
            self.company, external_id, name)

    def test_proposal_is_written_and_flagged(self):
        summary = self._apply()
        self.assertEqual(summary['created'], 1)
        row = self.product.okticket_tax_mapping_ids
        self.assertEqual(len(row), 1)
        self.assertEqual(row.okticket_rate, 10.0)
        self.assertEqual(row.tax_id, self.tax_10_s)
        self.assertTrue(row.auto_generated)

    def test_running_again_changes_nothing(self):
        """The scheduled job passes over every category every couple of hours."""
        self._apply()
        summary = self._apply()
        self.assertEqual(summary['created'], 0)
        self.assertEqual(summary['updated'], 0)
        self.assertEqual(summary['kept'], 1)
        self.assertEqual(len(self.product.okticket_tax_mapping_ids), 1)

    def test_an_edited_row_is_never_touched_again(self):
        self._apply()
        row = self.product.okticket_tax_mapping_ids
        row.write({'tax_id': self.other_tax.id})
        self.assertFalse(row.auto_generated, 'editing the tax takes ownership')
        summary = self._apply()
        self.assertEqual(summary['updated'], 0)
        self.assertEqual(row.tax_id, self.other_tax,
                         'the correction survives the next synchronisation')

    def test_a_proposed_row_follows_the_table(self):
        """How a change of criterion reaches installations: no migration."""
        self._apply()
        row = self.product.okticket_tax_mapping_ids
        row.with_context(okticket_auto_mapping=True).write(
            {'tax_id': self.other_tax.id})
        self.assertTrue(row.auto_generated)
        summary = self._apply()
        self.assertEqual(summary['updated'], 1)
        self.assertEqual(row.tax_id, self.tax_10_s)

    def test_a_category_of_its_own_is_left_alone(self):
        summary = self.product.okticket_apply_aeat_tax_defaults(
            self.company, 29958, 'Catering')
        self.assertEqual(summary['created'], 0)
        self.assertFalse(self.product.okticket_tax_mapping_ids)

    def test_fuel_is_mapped_as_goods(self):
        """The category the connector cannot resolve on its own, in any version."""
        fuel = self.env['product.template'].create({
            'name': 'Gasolina',
            'can_be_expensed': True,
        })
        fuel.okticket_apply_aeat_tax_defaults(self.company, 6, 'Gasolina')
        rates = fuel.okticket_tax_mapping_ids.mapped('okticket_rate')
        self.assertEqual(sorted(rates), [10.0, 21.0])
        self.assertEqual(
            fuel.okticket_tax_mapping_ids.filtered(
                lambda m: m.okticket_rate == 10.0).tax_id,
            self.tax_10_g, 'fuel is goods, not a service')

    def test_a_tax_the_chart_lacks_is_skipped_not_invented(self):
        """Normal on a database whose chart of accounts is not loaded yet."""
        self.assertFalse(self.env['product.template']._okticket_chart_tax(
            self.company, 'p_iva_that_no_chart_carries'))
        empty = self.env['product.template'].create({
            'name': 'Peaje',
            'can_be_expensed': True,
        })
        with self.patch_missing_chart():
            summary = empty.okticket_apply_aeat_tax_defaults(
                self.company, 3, 'Peaje')
        self.assertEqual(summary['created'], 0)
        self.assertEqual(len(summary['no_tax']), 1)
        self.assertFalse(empty.okticket_tax_mapping_ids)

    def patch_missing_chart(self):
        """Make every chart lookup come back empty, as before l10n_es is loaded."""
        return patch.object(
            type(self.env['product.template']), '_okticket_chart_tax',
            lambda self, company, suffix: self.env['account.tax'])

    def test_the_resolved_tax_reaches_okticket_mapped_tax(self):
        self._apply()
        self.assertEqual(
            self.product.okticket_mapped_tax(10.0, self.company.id),
            self.tax_10_s)
