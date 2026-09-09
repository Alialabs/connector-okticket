# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import base64
import datetime
import logging
import json

import requests
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

from . import hr_expense

_logger = logging.getLogger(__name__)


class HrExpenseBatchImporter(Component):
    _name = 'okticket.expenses.batch.importer'
    _inherit = 'okticket.import.mapper'
    _apply_on = 'okticket.hr.expense'
    _usage = 'importer'

    @mapping
    def name(self, record):
        return {
            'name': record.get('ticket_num') or record.get('name') or record.get('_id')
        }

    @mapping
    def description(self, record):
        # OkTicket sends the merchant in ``name`` and the user's note in
        # ``comments``. Both used to be mapped to ``description`` by two
        # separate mapping methods; because mappings are applied in
        # alphabetical order ``description`` always overwrote ``comments``,
        # so the user's note was never imported. Both are resolved here.
        return {
            'description': record.get('comments') or record.get('name') or False
        }

    @mapping
    def external_id(self, record):
        return {'external_id': record['_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        existing = self.env['hr.expense'].search(
            [('name', '=', record['_id'])],
            limit=1,
        )
        if existing:
            return {'odoo_id': existing.id}

    def get_base_product(self, record):
        params = [('okticket_type_prod_id', '=', record.get('type_id'))]
        if record.get('type_id') in [0, 1]:
            params.append(('okticket_categ_prod_id', '=', record.get('category_id')))
        existing = self.env['product.product'].search(params, limit=1)

        if 'custom_fields' in record and record['custom_fields'].get('refacturable') in [1, '1']:
            if existing.rebillable_prod_id:
                existing = self.env['product.product'].search(
                    [('product_tmpl_id', '=', existing.rebillable_prod_id.id)], limit=1
                )
        return existing

    def _pick_single_tax(self, taxes, product=None):
        """Narrow a set of same-rate purchase taxes down to a single one.

        A Spanish chart carries twelve purchase taxes per rate and they all have
        ``sequence = 1``, so taking the first one picks whatever id the database
        returns -- on the reference chart that is ``10% EX S``, an extra-community
        tax whose repartition sends +100% to input VAT and -100% to output VAT.
        It nets to zero, so a domestic 10% receipt lost its whole deductible VAT
        without a single error in the log.

        Two structural criteria, no name matching:

        * **Base taxes only.** A localisation that ships fiscal positions
          declares the domestic tax of a rate as the ``tax_src_id`` of the
          position mappings; the intra-community, import and reverse-charge
          variants appear only as ``tax_dest_id``, because they are reached *by
          translating* the base one. On the reference chart this alone takes the
          twelve candidates down to three (goods, services, capital goods).
        * **Matching scope.** ``tax_scope`` tells goods from services; an empty
          scope applies to both. Expense products are services, which leaves
          exactly one candidate for 4%, 10% and 21%.

        :return: a single-record recordset, or an empty one when the choice is
            not unambiguous -- never a guess.
        """
        if len(taxes) <= 1:
            return taxes
        src_ids = set(self.env['account.fiscal.position.tax'].search(
            [('tax_src_id', 'in', taxes.ids)]).mapped('tax_src_id').ids)
        base = taxes.filtered(lambda t: t.id in src_ids)
        if base:
            taxes = base
        if len(taxes) > 1 and product:
            scoped = taxes.filtered(lambda t: not t.tax_scope or t.tax_scope == product.type)
            if scoped:
                taxes = scoped
        return taxes if len(taxes) == 1 else self.env['account.tax']

    def _resolve_record_taxes(self, record, company_id, product=None):
        """Resolve Odoo purchase taxes from OkTicket's own ``taxes`` breakdown.

        OkTicket reports the real tax breakdown of the receipt as
        ``[{'p': <rate>, 'b': <base>}, ...]``. The connector ignored this field
        completely and always derived the taxes from the product's default
        supplier taxes, which is why an imported expense could show a tax that
        did not match the receipt at all.

        hr.expense holds a single taxable base, so a receipt combining several
        rates cannot be represented faithfully. In that case we log it and let
        the caller keep the product defaults rather than applying every rate to
        the whole base, which would inflate the tax.

        :return: list of account.tax ids, or None to keep the product defaults.
        """
        raw_taxes = record.get('taxes')
        if not raw_taxes or not company_id or not isinstance(raw_taxes, (list, tuple)):
            return None
        # OkTicket sends an entry for every rate it knows about and zeroes the
        # base of the ones the receipt does not use, e.g.
        #   [{p: 0, b: 0}, {p: 4, b: 0}, {p: 10, b: 0}, {p: 21, b: 14.88}]
        # so only entries with an actual base describe the receipt.
        rates = []
        for entry in raw_taxes:
            if not isinstance(entry, dict) or entry.get('p') is None:
                continue
            try:
                rate = float(entry['p'])
                base = float(entry.get('b') or 0)
            except (TypeError, ValueError):
                continue
            if base <= 0:
                continue
            if rate not in rates:
                rates.append(rate)
        if not rates:
            return None
        if len(rates) > 1:
            msg = _('Expense %s reports several tax rates (%s) but an Odoo expense '
                    'holds a single taxable base; keeping the product default taxes. '
                    'Review this expense manually.') % (
                record.get('_id'), ', '.join('%g%%' % r for r in rates))
            self.env['log.event'].add_event({
                'backend_id': self.backend_record.id,
                'type': 'warning',
                'msg': msg,
            })
            _logger.warning(msg)
            return None
        # Expense taxes are tax inclusive: hr.expense computes them with
        # ``force_price_include`` in the context, so the receipt total is always
        # treated as gross. The tax record's own ``price_include`` flag is
        # therefore irrelevant here and must not be used to filter -- a standard
        # Spanish chart carries none, so filtering on it would match nothing.
        candidates = self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', rates[0]),
            ('company_id', '=', company_id),
        ])
        if not candidates:
            _logger.warning('No purchase tax of %g%% found in company %s for expense %s; '
                            'keeping the product default taxes',
                            rates[0], company_id, record.get('_id'))
            return None
        # Resolution chain, from the most explicit to the most inferred. None of
        # the steps ever falls back to "whatever the database returns first".
        if product is not None:
            # 1) What the product (or the base product it derives from) declares
            #    for this rate. Explicit configuration always wins, and it is the
            #    only way to say that a rate is goods here: the connector types
            #    every expense product as a service, so ``_pick_single_tax``
            #    below can only ever reach the services variant.
            mapped = product.product_tmpl_id.okticket_mapped_tax(
                rates[0], company_id)
            if mapped:
                return mapped.ids
        # 2) A tax the product already carries: same chart context, deterministic.
        own = candidates & product.supplier_taxes_id if product else self.env['account.tax']
        # 3) Structural disambiguation.
        picked = self._pick_single_tax(own, product) or self._pick_single_tax(candidates, product)
        if picked:
            return picked.ids
        # Ambiguous: import the expense with no tax rather than with an invented
        # one, and say which candidates could not be told apart. Returning an
        # empty list is not the same as returning None -- None means "no usable
        # rate reported", and the caller keeps the product defaults for that.
        msg = _('Expense %s reports %g%% but that rate matches several purchase '
                'taxes in company %s that cannot be told apart (%s); imported '
                'with no tax. Map the rate on the product\'s OkTicket tab, or '
                'add the right tax to the product.') % (
            record.get('_id'), rates[0], company_id,
            ', '.join(candidates.mapped('name')))
        self.env['log.event'].add_event({
            'backend_id': self.backend_record.id,
            'type': 'warning',
            'msg': msg,
        })
        _logger.warning(msg)
        return []

    @mapping
    def product_id(self, record):
        existing = self.get_base_product(record)
        company_id = (self.company_id(record) or {}).get('company_id')
        if existing:
            result = {'product_id': existing.id}
            # The tax OkTicket reports for the receipt comes first, whatever the
            # expense type. Taxes used to be resolved only for type_id != 0, so a
            # plain ticket whose receipt says 10% silently ended up with the
            # product's default 21% -- measured on the demo company: 17 of 44.
            record_tax_ids = self._resolve_record_taxes(record, company_id,
                                                        product=existing)
            if record_tax_ids is not None:
                # An empty list is deliberate: the rate was reported but could
                # not be resolved to a single tax, so no tax is better than the
                # product's unrelated default.
                result.update({'tax_ids': [(6, 0, record_tax_ids)]})
            else:
                # OkTicket reported no usable rate, or Odoo has no tax with it:
                # fall back to the product's own supplier taxes.
                tax_ids = [(4, stax.id) for stax in existing.supplier_taxes_id
                           if stax.company_id.id == company_id]
                if tax_ids:
                    result.update({'tax_ids': tax_ids})
            return result

    @mapping
    def amount(self, record):
        if record.get('amount') is None:
            # Never import a silent 0.00 expense: leaving the amount out makes
            # the required-fields check skip and log the record instead of
            # letting it reach accounting with a wrong amount.
            return
        # ``total_amount_currency`` and not ``total_amount``: the amount fields
        # form a compute cycle in Odoo 18 -- ``total_amount_currency`` derives
        # from ``price_unit``, ``price_unit`` from both totals, and the tax
        # breakdown from ``total_amount_currency``. Writing ``total_amount``
        # relied on its inverse, which runs *after* the precomputes and leaves
        # ``untaxed_amount_currency`` / ``tax_amount_currency`` at the 0.00 they
        # got while the total was still empty; Odoo protects the fields an
        # inverse touches, so they were never recomputed and every expense
        # reached accounting with no VAT split at all.
        # ``total_amount_currency`` is readonly=False precisely to be written,
        # and Odoo derives the rest from it.
        return {
            'total_amount_currency': record['amount'],
        }

    @mapping
    def date(self, record):
        if record.get('date'):
            date_time = datetime.datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S')
            return {'date': date_time.date()}

    def _get_expense_company(self, record):
        """Resolve the Odoo company for the expense.

        The analytic/account lookups below are pinned to ``self.backend_record``,
        so the company must be the one of that same backend: resolving it from
        any backend matching the payload could create the expense in company B
        while referencing company A's bindings, which is exactly the
        ``check_company`` "Incompatible companies" error we want to avoid.

        Returns an empty recordset when the payload belongs to another OkTicket
        company, so the caller skips and logs the record instead of importing it
        with cross-company references.
        """
        raw_company_id = record.get('company_id')
        if raw_company_id:
            # The API is not consistent about id types (ids arrive as int or as
            # str depending on the endpoint), so compare as int and fail open:
            # on anything non-numeric keep the backend company rather than
            # dropping the expense.
            try:
                if int(raw_company_id) != int(self.backend_record.okticket_company_id or 0):
                    return self.env['res.company'].browse()
            except (TypeError, ValueError):
                _logger.warning(
                    'Unexpected OkTicket company_id %r on expense %s; '
                    'falling back to the backend company',
                    raw_company_id, record.get('_id'))
        return self.backend_record.company_id

    @mapping
    def company_id(self, record):
        company = self._get_expense_company(record)
        if company:
            return {'company_id': company.id}

    @mapping
    def employee_id(self, record):
        if not record.get('user_id'):
            return
        domain = [('okticket_user_id', '=', record['user_id'])]
        # Prefer an employee of the expense company, since hr.expense enforces
        # check_company on employee_id. But fall back to an unscoped lookup:
        # a very common layout keeps every employee in the parent company while
        # each backend maps to a child company, and scoping strictly there would
        # leave employee_id unresolved and drop every expense.
        company = self._get_expense_company(record)
        existing = self.env['hr.employee'].browse()
        if company:
            existing = self.env['hr.employee'].search(
                domain + [('company_id', '=', company.id)], limit=1
            )
        if not existing:
            existing = self.env['hr.employee'].search(domain, limit=1)
        if existing:
            return {'employee_id': existing.id}

    @mapping
    def okticket_status(self, record):
        if record.get('status_id') is None:
            # Do not assert "pending" for an unknown status: leave the field
            # default rather than reporting a state OkTicket never sent.
            return
        return {'okticket_status': 'confirmed' if record['status_id'] == 1 else 'pending'}

    @mapping
    def okticket_vat(self, record):
        if 'cif' in record:
            return {'okticket_vat': record['cif']}

    @mapping
    def okticket_partner_name(self, record):
        if 'name' in record:
            return {'okticket_partner_name': record['name']}

    @mapping
    def okticket_remote_path(self, record):
        if 'remote_path' in record:
            return {'okticket_remote_path': record['remote_path']}

    @mapping
    def okticket_remote_uri(self, record):
        if 'remote_uri' in record:
            img_path = self.backend_record.image_base_url + record['remote_uri']
            result = {'okticket_remote_uri': record['remote_uri']}
            # This download had no timeout and no error handling: an unresponsive
            # image host hung the whole import, and an HTML error page was stored
            # base64-encoded as if it were the receipt image.
            try:
                response = requests.get(img_path, timeout=60)
                if response.ok and response.content:
                    result['okticket_img'] = base64.b64encode(response.content)
                else:
                    _logger.warning('Could not download expense image %s (HTTP %s)',
                                    img_path, response.status_code)
            except Exception as e:
                _logger.warning('Error downloading expense image %s: %s', img_path, e)
            return result

    @mapping
    def okticket_response(self, record):
        try:
            res = json.dumps(record, indent=4, sort_keys=True)
        except Exception:
            res = ''
        return {'okticket_response': res}

    @mapping
    def payment_method(self, record):
        payment_method = 'na'
        if record.get('payment_method') and \
            record['payment_method'] in [method[0] for method in hr_expense._payment_method_selection]:
            payment_method = record['payment_method']
        return {'payment_method': payment_method}

    @mapping
    def payment_mode(self, record):
        payment_mode = 'own_account' if record.get('payment_method') == 'efectivo' else 'company_account'

        if record.get('custom_fields') and record['custom_fields'].get('refundable'):
            payment_mode = 'own_account'
            if record['custom_fields']['refundable'] == 'payed':
                payment_mode = 'company_account'

        return {'payment_mode': payment_mode}

    @mapping
    def analytic_account_id(self, record):
        if record.get('cost_center_id'):
            cc_analytic_binder = self.env['okticket.account.analytic.account'].search(
                [('external_id', '=', int(record['cost_center_id'])),
                 ('backend_id', '=', self.backend_record.id)], limit=1
            )

            if cc_analytic_binder and cc_analytic_binder.odoo_id:
                fields = {
                    'analytic_account_id': cc_analytic_binder.odoo_id.id,
                    'analytic_distribution': {cc_analytic_binder.odoo_id.id: 100}
                }
                sale_order = cc_analytic_binder.odoo_id.get_related_sale_order()
                if sale_order:
                    fields.update({'sale_order_id': sale_order.id})
                return fields

    @mapping
    def account_id(self, record):
        """
        The ledger account of the related project is preferably assigned.
        If it does not have any, it is searched from within the product.
        """
        okticket_account_id = False
        if record.get('cost_center_id'):
            cc_analytic_binder = self.env['okticket.account.analytic.account'].search(
                [('external_id', '=', int(record['cost_center_id'])),
                 ('backend_id', '=', self.backend_record.id)], limit=1
            )
            if cc_analytic_binder and cc_analytic_binder.odoo_id:
                okticket_account_id = cc_analytic_binder.odoo_id.okticket_def_account_id.id if cc_analytic_binder.odoo_id.okticket_def_account_id else False
        if not okticket_account_id:
            existing = self.get_base_product(record)
            if existing.property_account_expense_id:
                okticket_account_id = existing.property_account_expense_id.id
        if okticket_account_id:
            return {'account_id': okticket_account_id}

    # @mapping
    # def reference(self, record):
    #     return {'reference': record.get('ticket_num') or 'N.A.'}

    @mapping
    def is_invoice(self, record):
        return {'is_invoice': record.get('type_id') == 1}

    def _import_pdf_to_chatter(self, binding, record):
        """Download the OkTicket PDF (invoices/tickets sent to the robot) and
        attach it to the related hr.expense chatter.

        The connector only downloads the JPG preview (``remote_uri``) into
        ``okticket_img``; the actual PDF lives in ``signed_pdf_url`` (a
        pre-signed S3 URL). This brings that PDF into Odoo so it is available
        on the expense. Idempotent: it is not re-attached on later imports.

        Must be called outside the expense savepoint: it performs a blocking
        HTTP download and its own writes, so it must neither hold the expense
        transaction open nor leave the cursor aborted for the next iteration.
        """
        pdf_url = record.get('signed_pdf_url')
        if not pdf_url or not binding or not binding.odoo_id:
            return
        expense = binding.odoo_id
        filename = '%s.pdf' % (record.get('ticket_num') or record.get('_id') or 'okticket')
        already = self.env['ir.attachment'].sudo().search_count([
            ('res_model', '=', 'hr.expense'),
            ('res_id', '=', expense.id),
            ('name', '=', filename),
        ])
        if already:
            return
        try:
            response = requests.get(pdf_url, timeout=60)
            if not response.ok or not response.content:
                _logger.warning('Could not download expense PDF %s (HTTP %s)',
                                pdf_url, response.status_code)
                return
            # Own savepoint: a DB error here must roll back to a clean state
            # instead of leaving the cursor aborted, which would make every
            # remaining expense of the import fail with InFailedSqlTransaction.
            with self.env.cr.savepoint():
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'datas': base64.b64encode(response.content),
                    'res_model': 'hr.expense',
                    'res_id': expense.id,
                    'mimetype': 'application/pdf',
                })
                expense.sudo().message_post(
                    body=_('OkTicket PDF document imported'),
                    attachment_ids=[attachment.id],
                )
        except Exception as e:
            _logger.warning('Error importing expense PDF %s: %s', pdf_url, e)

    def run(self, filters=None, options=None):
        backend_adapter = self.component(usage='backend.adapter')
        okticket_hr_expense_ids = []
        mapper = self.component(usage='importer')
        binder = self.component(usage='binder')

        # 'total_amount_currency' is required so an expense whose payload carries
        # no amount is skipped and logged instead of imported as 0.00.
        required_fields = ['product_id', 'employee_id', 'company_id',
                           'total_amount_currency']

        filters, last_expenses_import = self.datetime_expenses_import_backend_filter(filters)
        only_reviewed = self.backend_record.import_only_reviewed_expenses

        expense_records = backend_adapter.search(filters)
        # A listing cut short by an API error must not move the watermark: the
        # records that were never fetched are older than the new cut-off, so
        # they would fall out of the incremental window for good. Measured on
        # the reference company: a 500 halfway through returned 640 records
        # instead of 642, raising nothing, and the two missing ones would never
        # have been asked for again.
        listing_truncated = backend_adapter.last_listing_was_truncated()

        for expense_ext_vals in expense_records:
            try:
                # Searchs if the OkTicket id already exists in odoo
                binding = binder.to_internal(expense_ext_vals.get('_id'))

                # Gasto eliminado (lógico) en Okticket
                if 'deleted_at' in expense_ext_vals and expense_ext_vals['deleted_at']:  # deleted_at not null
                    if binding:
                        self.delete_expense_synchro(binding)
                    continue

                # Restricción de importación de gastos revisados
                if only_reviewed and expense_ext_vals and \
                    ('review' not in expense_ext_vals or not expense_ext_vals['review']):
                    continue

                # Map to odoo data
                internal_data = mapper.map_record(expense_ext_vals).values()

                # Check and log missing required fields
                missing_fields = [field for field in required_fields if field not in internal_data]
                if missing_fields:
                    msg = _('Importing expense ID: %s. It does not have required fields: %s') % (
                        expense_ext_vals.get('_id'), missing_fields)
                    log_vals = {
                        'backend_id': self.backend_record.id,
                        'type': 'warning',
                        'msg': msg,
                    }
                    self.env['log.event'].add_event(log_vals)
                    _logger.error(msg)
                    continue

                company_id = internal_data.get('company_id')
                with self.env.cr.savepoint():
                    if binding:
                        _logger.info('Updating expense with employee_id: %s', internal_data.get('employee_id'))
                        if internal_data.get('employee_id') is None:
                            _logger.error('Employee ID is missing for expense ID: %s', expense_ext_vals.get('_id'))
                            continue
                        binding.with_company(company_id).sudo().write(internal_data)
                    else:
                        if any(field not in internal_data for field in required_fields):
                            missing_fields = [field for field in required_fields if field not in internal_data]
                            msg = _('Importing expense ID: %s. It does not have required fields: %s') % (
                                expense_ext_vals.get('_id'), missing_fields)
                            log_vals = {
                                'backend_id': self.backend_record.id,
                                'type': 'warning',
                                'msg': msg,
                            }
                            self.env['log.event'].add_event(log_vals)
                            _logger.error(msg)
                            continue
                        binding = self.model.with_company(company_id).sudo().create(internal_data)

                    okticket_hr_expense_ids.append(binding.id)
                    binder.bind(expense_ext_vals.get('_id'), binding)
                    _logger.info('Imported')

                # Outside the savepoint on purpose: this downloads the PDF over
                # HTTP (up to the request timeout) and must not hold the expense
                # transaction open, nor abort it if the attachment write fails.
                self._import_pdf_to_chatter(binding, expense_ext_vals)

                if not listing_truncated:
                    self.backend_record.import_expenses_since = last_expenses_import
            except Exception as e:
                msg = _('\nError: %s\n') % e
                log_vals = {
                    'backend_id': self.backend_record.id,
                    'type': 'error',
                    'msg': msg,
                }
                self.env['log.event'].add_event(log_vals)
                _logger.error(msg)

        if listing_truncated:
            msg = _('The OkTicket expense listing was cut short by an API error, so '
                    '%(imported)s expenses were imported out of an unknown total. '
                    '"Import Expenses since" has been left untouched on purpose, so the '
                    'next run asks for the same range again instead of skipping what '
                    'never arrived.') % {'imported': len(okticket_hr_expense_ids)}
            self.env['log.event'].add_event({
                'backend_id': self.backend_record.id,
                'type': 'warning',
                'msg': msg,
            })
            _logger.warning(msg)

        _logger.info('Import from Okticket DONE')
        return okticket_hr_expense_ids

    def datetime_expenses_import_backend_filter(self, filters):
        last_expenses_import = datetime.datetime.now()
        if not self.backend_record.ignore_import_expenses_since and self.backend_record.import_expenses_since:
            # Restricción de importación de gastos por fecha de última importación
            filters = filters or {}
            filters.update({
                'params': {
                    'updated_after': self.backend_record.import_expenses_since.strftime("%Y-%m-%dT%H:%M:%S")
                }
            })
        else:
            # All expenses not in "sent" state (this is, state = "draft") are deleted before new import or
            # synchronization of expenses from OkTicket. This way, we ensure Odoo-OkTicket synchronization.
            states_to_remove = ['draft']
            company_id = self.backend_record.company_id.id
            expenses_to_remove = self.env['hr.expense'].search([
                ('state', 'in', states_to_remove),
                ('company_id', '=', company_id)
            ]).filtered(lambda exp: exp.okticket_expense_id)
            expenses_to_remove.unlink()
        return filters, last_expenses_import
