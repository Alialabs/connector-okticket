# Copyright 2026 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Which Odoo tax an OkTicket rate means, derived from Spanish VAT law.

Reference data for pre-filling ``okticket.product.tax.mapping`` when a category
is imported and its product created. Two tables:

* ``BASE_TAX_BY_RATE_SCOPE`` -- the Odoo tax that stands for a (rate, nature)
  pair in the Spanish chart.
* ``OKTICKET_DEFAULT_CATEGORIES`` -- the rates Spanish VAT law admits for each
  of OkTicket's fourteen default categories, and whether each one arrives as a
  supply of goods or of services.

**The source is the law, not OkTicket.** The API does publish its own answer
(``iva`` on the category plus a ``tax_ids`` catalogue), and it was deliberately
not used: measured against the reference company it is both incomplete -- the
"Otros" and "Alojamiento" categories declare no Spanish VAT rate at all, only
IGIC and IPSI -- and too narrow, since "Restauración" declares only 10% while a
receipt filed there may legitimately carry 21% or 4%. Seeding from it would
write mappings that are wrong in law.

A row is a *lookup*, never a default: it says "if a receipt reports this rate,
this is the Odoo tax", so listing a rate here never forces it on an expense.
That is why the temporary rates need no special handling -- the rate arrives on
the receipt and the row only has to know what it means. It is also why a rate
this table does not list is worth a warning rather than a silent fallback: on a
train ticket 21% is not a rate, it is a mistake.

Territorial scope: IVA only (art. 3 LIVA). Receipts from the Canary Islands,
Ceuta and Melilla carry IGIC or IPSI, have no counterpart in a peninsular chart
and are not covered here; OkTicket reports which one applies in the expense's
own ``tax_model_id``.

Some categories admit two operations that carry the *same* rate and differ only
in nature or in why they are zero: a restaurant meal at 10% as a service and
take-away food at 10% as goods, an exempt international flight and a rail leg
that is simply not subject. Both readings are right in law and only one can be
declared, because a mapping row is keyed by product, company and rate. The
receipt carries a rate and a base and nothing else, so no table can tell the
two apart -- that is a product-level decision (a separate category for
take-away, say), not a rate-level one. Each such case is recorded in the category's
``collisions`` note so the reasoning is not lost.

Rates and articles verified against the AEAT table "Tipos impositivos en el IVA
2026" (26/02/2026) and Ley 37/1992.
"""

import unicodedata

# ---------------------------------------------------------------------------
# Chart taxes
# ---------------------------------------------------------------------------
# Keys are the suffix of the tax template's XML id; the record to look up is
# ``<company_id>_account_tax_template_<suffix>`` in ``ir.model.data``. The
# module that owns it changed between versions -- ``l10n_es`` up to 16.0,
# ``account`` from 17.0 on -- but the technical names did not, so this table is
# version independent and the lookup must not filter by module. Verified on
# both charts: 'PGCE PYMEs 2008' (16.0) and 'es_pymes' (18.0).
#
# Only the *base* taxes of each rate appear here: the intra-community, import
# and reverse-charge variants are reached by translating the base one through a
# fiscal position, never by an expense import.
BASE_TAX_BY_RATE_SCOPE = {
    # (rate, nature): XML id suffix                   # chart name (18.0)
    (21.0, 'service'): 'p_iva21_sc',                  # 21% S
    (21.0, 'consu'): 'p_iva21_bc',                    # 21% G
    (10.0, 'service'): 'p_iva10_sc',                  # 10% S
    (10.0, 'consu'): 'p_iva10_bc',                    # 10% G
    (4.0, 'service'): 'p_iva4_sc',                    # 4% S
    (4.0, 'consu'): 'p_iva4_bc',                      # 4% G
    (0.0, 'service'): 'p_iva0_s_sc',                  # 0% S
    (0.0, 'consu'): 'p_iva0_s_bc',                    # 0% G
}

# Zero rate, three different meanings, three different taxes. They all arrive on
# the receipt as 0% (or as no breakdown at all), so a category can declare only
# one of them -- see the note on collisions below.
#
#   exempt with credit   art. 22 and art. 21.5º/23/24   -> ``p_iva0_s_sc`` (0% S)
#   not subject          art. 70.Uno.2º, the leg run outside Spanish VAT
# #                        territory                      -> ``p_iva0_ns`` (0%
#                                  S EXEMPT NS)
#   exempt, current op.  no credit                      -> ``p_iva0_bc`` (0% EXEMPT OP)
NON_SUBJECT_TAX_BY_SCOPE = {
    'service': 'p_iva0_ns',
    'consu': 'p_iva0_ns_b',
}

# Investment goods (``p_iva21_bi`` and friends) are deliberately absent. They
# share rate, scope and base condition with the current-goods tax, which is
# exactly why the connector cannot tell them apart on its own and why a goods
# category needs a declared row even in 18.0. Capitalising an expense is a
# decision nobody can take from a receipt.

# Non-deductible variants, for expenses that are not deductible input VAT --
# client entertainment being the usual one (art. 96 LIVA). Never seeded: no
# category tells us the expense was entertainment. Listed so the commissioning
# has the technical names to hand, because these taxes carry no ``tax_scope``
# and are not a fiscal position source, so the connector can never reach them
# by inference either.
NON_DEDUCTIBLE_TAX_BY_RATE = {
    # The 21% one really is named after 0%: an l10n_es quirk kept for
    # compatibility, present identically in 16.0 and 18.0. Not a typo.
    21.0: 'p_iva0_nd',
    10.0: 'p_iva10_nd',
    4.0: 'p_iva4_nd',
}

# Partial deduction on vehicle running costs (the 50% presumption of art.
# 95.Tres.2ª LIVA, which reaches Gasolina, Aparcamiento, Peaje and Alquiler
# vehículo) has no tax of its own in either chart and is not modelled here.

# ---------------------------------------------------------------------------
# OkTicket default categories
# ---------------------------------------------------------------------------
# Ids 0-6 and 4301-4307 are OkTicket's global categories: same ids for every
# customer, ``company_id`` null. A customer's own categories are not seeded --
# nothing states their nature.
#
# ``nature``  what the category is in VAT terms, and therefore the ``tax_scope``
#             a rate not listed in ``rates`` would take if it ever arrives.
# ``rates``   rate -> nature of the operation that carries it. The nature is per
#             *rate*, not per category: a meal is a service at 10% while the
#             bottle of wine bought at the same counter is a good at 21%.
OKTICKET_DEFAULT_CATEGORIES = {
    0: {
        'name': 'Otros',
        'nature': None,
        'rates': {},
        'legal': 'No nature and no rate can be stated for a catch-all '
                 'category: it holds anything from a hotel extra to a box of '
                 'pens. The law gives nothing to seed here, so every rate is '
                 'left to the service fallback below -- which is a decision '
                 'about what to do when nobody decided, not a legal criterion. '
                 'Correct the row on the product when a receipt says otherwise: '
                 'from then on the connector leaves it alone.',
    },
    1: {
        'name': 'Restauración',
        'nature': 'service',
        'rates': {10.0: 'service', 21.0: 'consu', 4.0: 'consu'},
        'legal': '10% for hospitality and restaurant services and for the '
                 'supply of food and drink consumed on the spot (art. '
                 '91.Uno.2.2º) -- alcohol served at the table included, and '
                 'since 2026 mixed hospitality services (discotheques, '
                 'function rooms) as well. Alcoholic drinks and sweetened soft '
                 'drinks bought as goods are excluded from the reduced rate by '
                 'art. 91.Uno.1.1º and therefore taxed at the standard rate of '
                 'art. 90.Uno. 4% for staple food as goods -- bread, milk, '
                 'cheese, eggs, fruit, vegetables, pulses, cereals and olive '
                 'oil (art. 91.Dos.1.1º).',
        'collisions': 'Take-away and delivery of prepared food is a supply of '
                      'goods at 10% (art. 91.Uno.1.1º), not a service, and a '
                      'function room invoiced separately is a service at 21% '
                      '(art. 90.Uno). Both are right in law and neither can be '
                      'declared: they share a rate with the row above.',
    },
    2: {
        'name': 'Aparcamiento',
        'nature': 'service',
        'rates': {21.0: 'service'},
        'legal': 'Letting of a parking space is a supply of services (art. '
                 '11.Dos.2º) at the standard rate (art. 90.Uno); it appears in '
                 'no reduced rate list.',
    },
    3: {
        'name': 'Peaje',
        'nature': 'service',
        'rates': {21.0: 'service'},
        'legal': 'Standard rate (art. 90.Uno). A toll pays for the use of the '
                 'road, not for passenger transport, so the 10% of art. '
                 '91.Uno.2.1º does not reach it.',
    },
    4: {
        'name': 'Transporte',
        'nature': 'service',
        'rates': {10.0: 'service', 0.0: 'service'},
        'legal': '10% for the transport of passengers and their luggage (art. '
                 '91.Uno.2.1º). 0% for international transport by air or sea, '
                 'exempt with credit under art. 22.Trece.',
        'collisions': 'Art. 70.Uno.2º locates passenger transport where it is '
                      'run, so the leg outside Spanish VAT territory is not '
                      'subject rather than exempt -- a different tax '
                      '(``p_iva0_ns``) at the same 0%. The exemption is kept '
                      'here because it is the common case on an air or sea '
                      'ticket.',
    },
    5: {
        'name': 'Alojamiento',
        'nature': 'service',
        'rates': {10.0: 'service', 21.0: 'service'},
        'legal': '10% as a hospitality service (art. 91.Uno.2.2º). 21% for '
                 'non-hospitality extras invoiced separately on the same bill '
                 '-- parking, meeting rooms -- which fall under art. 90.Uno.',
        'collisions': 'A closed bottle from the minibar or anything bought at '
                      'the hotel shop is a supply of goods at 21% (art. '
                      '90.Uno), sharing the rate with the extras row above.',
    },
    6: {
        'name': 'Gasolina',
        'nature': 'consu',
        'rates': {21.0: 'consu', 10.0: 'consu'},
        'legal': 'A supply of goods, and the only default category that is. '
                 '21% is the rate in force (art. 90.Uno). 10% applied to '
                 'petrol, diesel and biofuels under art. 42 of RDL 7/2026 of '
                 '20 March, between 22/03/2026 and 30/06/2026 only; it was not '
                 'extended (RDL 18/2026 replaced it with a cut in the '
                 'hydrocarbon duty), so from 01/07/2026 the rate is 21% again '
                 'and the 10% row is there for receipts of that window. Being '
                 'goods, this is the category the connector cannot resolve on '
                 'its own in any version: current goods and investment goods '
                 'share rate, scope and base condition.',
    },
    4301: {
        'name': 'Bus',
        'nature': 'service',
        'rates': {10.0: 'service'},
        'legal': 'Transport of passengers and their luggage, art. 91.Uno.2.1º.',
    },
    4302: {
        'name': 'VTC',
        'nature': 'service',
        'rates': {10.0: 'service'},
        'legal': 'Transport of passengers and their luggage, art. 91.Uno.2.1º.',
    },
    4303: {
        'name': 'Alquiler vehículo',
        'nature': 'service',
        'rates': {21.0: 'service'},
        'legal': 'Renting without a driver is a supply of services (art. '
                 '11.Dos.2º) at the standard rate (art. 90.Uno): it carries no '
                 'passenger transport, so no reduced rate applies.',
        'collisions': 'A lease whose purchase option is committed is a supply '
                      'of goods from the outset (art. 8.Dos.5º), also at 21%. '
                      'It does not reach an expense report as a ticket, and it '
                      'would share the rate with the row above.',
    },
    4304: {
        'name': 'Taxi',
        'nature': 'service',
        'rates': {10.0: 'service'},
        'legal': 'Transport of passengers and their luggage, art. 91.Uno.2.1º.',
    },
    4305: {
        'name': 'Tren',
        'nature': 'service',
        'rates': {10.0: 'service', 0.0: 'service'},
        'overrides': {0.0: 'p_iva0_ns'},
        'legal': '10% for the transport of passengers and their luggage (art. '
                 '91.Uno.2.1º). The exemption of art. 22.Trece covers air and '
                 'sea only, so a cross-border rail journey is not exempt: the '
                 'leg run outside Spanish VAT territory is simply not subject '
                 '(art. 70.Uno.2º), which is why the 0% row points at the '
                 'not-subject tax and not at the exempt one.',
    },
    4306: {
        'name': 'Avión',
        'nature': 'service',
        'rates': {10.0: 'service', 0.0: 'service'},
        'legal': '10% on domestic flights (art. 91.Uno.2.1º). International '
                 'flights are exempt with credit (art. 22.Trece), which is the '
                 '0% row -- and one of the cases the connector can never '
                 'resolve by inference, since the chart carries five different '
                 'base taxes at 0%.',
    },
    4307: {
        'name': 'Otros Transportes',
        'nature': 'service',
        'rates': {10.0: 'service', 21.0: 'service', 0.0: 'service'},
        'legal': '10% when it carries passengers (art. 91.Uno.2.1º); 21% when '
                 'it carries goods -- freight and courier services have no '
                 'reduced rate (art. 90.Uno); 0% when the carriage is linked '
                 'to an export or to an import whose cost is already in the '
                 'customs value, exempt with credit under arts. 21.5º, 23 and '
                 '24.',
    },
}


def _normalise(name):
    """Fold a category name for comparison: no case, no accents, no padding."""
    if not name:
        return ''
    folded = unicodedata.normalize('NFKD', name)
    folded = ''.join(c for c in folded if not unicodedata.combining(c))
    return ' '.join(folded.lower().split())


def resolve_category(external_id, name):
    """The default category a (id, name) pair stands for, or ``None``.

    Both come from the same API payload, which is why this is decided on every
    masters synchronisation instead of being stored: the run always holds the
    live values and never depends on an id written months ago.

    The id alone is not enough to accept a match. OkTicket's default categories
    carry no company and look like a catalogue shared by every tenant, but that
    has only been observed on one, so an id that means "Taxi" here could mean
    something else elsewhere. Applying a tax criterion to the wrong kind of
    expense is worse than applying none, so the name has to corroborate it.

    :param external_id: the category id in OkTicket.
    :param name: the category name in OkTicket, as the payload spells it.
    :return: ``(category_id, entry, exact)`` where ``exact`` is False when the
        name matched but the id did not, or ``None`` when nothing matched.
    """
    try:
        external_id = int(external_id)
    except (TypeError, ValueError):
        external_id = None
    folded = _normalise(name)
    entry = OKTICKET_DEFAULT_CATEGORIES.get(external_id)
    if entry and _normalise(entry['name']) == folded:
        return external_id, entry, True
    # The id did not match, or matched a different category: fall back to the
    # name, which is the business meaning of the catalogue. A bare id match is
    # deliberately *not* accepted -- it is the half of the evidence that was
    # assumed to drift.
    if folded:
        for cat_id, candidate in OKTICKET_DEFAULT_CATEGORIES.items():
            if _normalise(candidate['name']) == folded:
                return cat_id, candidate, False
    return None


# The rates OkTicket can report. A receipt never carries anything else: the
# API sends an entry for each of them and zeroes the base of the ones the
# document does not use.
OKTICKET_REPORTED_RATES = (21.0, 10.0, 4.0, 0.0)


def service_fallback_rows(category_id):
    """Service rows for the rates the category's legal criterion leaves open.

    Without them a rate the table says nothing about has no tax to resolve to,
    and the two sides of the connector disagree on what to do: the expense
    import falls back to the product's default tax while the invoice, which
    needs one tax *per rate*, refuses. The customer's decision is to close that
    gap with the services variant, which is also the nature every expense
    product is typed as.

    They are a default, not a legal statement: a category whose law says a rate
    is goods -- fuel, staple food -- declares it in the table above and that row
    wins. This only fills what nobody decided.

    :param category_id: the OkTicket category id (its ``external_id``).
    :return: list of ``(rate, scope, tax_xmlid_suffix)``.
    """
    category = OKTICKET_DEFAULT_CATEGORIES.get(category_id)
    if category is None:
        return []
    declared = set(category['rates'])
    rows = []
    for rate in OKTICKET_REPORTED_RATES:
        if rate in declared:
            continue
        suffix = BASE_TAX_BY_RATE_SCOPE.get((rate, 'service'))
        if suffix:
            rows.append((rate, 'service', suffix))
    return rows


def category_tax_rows(category_id):
    """The rows Spanish VAT law admits for an OkTicket default category.

    :param category_id: the OkTicket category id (its ``external_id``).
    :return: list of ``(rate, scope, tax_xmlid_suffix)``, empty for a category
        this table does not cover -- a customer's own category, or "Otros".
    """
    category = OKTICKET_DEFAULT_CATEGORIES.get(category_id)
    if not category:
        return []
    rows = []
    overrides = category.get('overrides') or {}
    for rate, scope in sorted(category['rates'].items(), reverse=True):
        suffix = overrides.get(rate) or BASE_TAX_BY_RATE_SCOPE.get((rate, scope))
        if suffix:
            rows.append((rate, scope, suffix))
    return rows
