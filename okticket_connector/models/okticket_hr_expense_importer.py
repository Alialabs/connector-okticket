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
        return {
            'description': record.get('name') or False
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

    @mapping
    def product_id(self, record):
        existing = self.get_base_product(record)
        company_id = (self.company_id(record) or {}).get('company_id')
        if existing:
            result = {'product_id': existing.id}
            if record.get('type_id') != 0:
                #tax_ids = [(4, stax.id) for stax in existing.supplier_taxes_id]
                tax_ids = [(4, stax.id) for stax in existing.supplier_taxes_id if stax.company_id.id == company_id]
                if tax_ids:
                    result.update({'tax_ids': tax_ids})
            return result

    @mapping
    def amount(self, record):
        return {
            'price_unit': 0.0,  # Para hacer visibles los impuestos en la interfaz Odoo 15
            'total_amount': record.get('amount', 0.0)
        }

    @mapping
    def date(self, record):
        if record.get('date'):
            date_time = datetime.datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S')
            return {'date': date_time.date()}

    @mapping
    def comments(self, record):
        if 'comments' in record:
            return {'description': record['comments']}

    @mapping
    def company_id(self, record):
        if record.get('company_id'):
            backend = self.env['okticket.backend'].search(
                [('okticket_company_id', '=', record['company_id'])], limit=1
            )
            if backend:
                return {'company_id': backend.company_id.id}

    @mapping
    def employee_id(self, record):
        if record.get('user_id'):
            domain = [('okticket_user_id', '=', record['user_id'])]
            company_vals = self.company_id(record)
            if company_vals and company_vals.get('company_id'):
                # The employee must belong to the same company as the expense
                domain.append(('company_id', '=', company_vals['company_id']))
            existing = self.env['hr.employee'].search(domain, limit=1)
            if existing:
                return {'employee_id': existing.id}

    @mapping
    def okticket_status(self, record):
        return {'okticket_status': 'confirmed' if record.get('status_id') == 1 else 'pending'}

    @mapping
    def okticket_report_id(self, record):
        if 'report_id' in record:
            return {'okticket_report_id': record['report_id']}

    @mapping
    def okticket_report_name(self, record):
        report_id = record.get('report_id')
        return {'okticket_report_name': self._get_okticket_report_name(report_id)}

    def _get_okticket_report_name(self, report_id):
        """Fetch the OkTicket report name, cached per import run."""
        if not report_id:
            return False
        if not hasattr(self, '_report_name_cache'):
            self._report_name_cache = {}
        if report_id not in self._report_name_cache:
            name = False
            try:
                adapter = self.component(usage='backend.adapter')
                if adapter._auth():
                    result = adapter.okticket_api.find_report_by_id(
                        report_id, https=self.backend_record.https)
                    report = result.get('result')
                    if isinstance(report, dict) and 'data' in report:
                        report = report['data']
                    if isinstance(report, list):
                        report = report[0] if report else {}
                    name = (report or {}).get('name')
            except Exception:
                _logger.warning(
                    'Could not fetch OkTicket report %s name', report_id)
            self._report_name_cache[report_id] = name
        return self._report_name_cache[report_id]

    @mapping
    def okticket_vat(self, record):
        if 'cif' in record:
            return {'okticket_vat': record['cif']}

    @mapping
    def vendor_id(self, record):
        """Fill the vendor when the captured VAT matches exactly one partner.

        The comparison takes the country prefix into account: a captured
        VAT without prefix matches a partner VAT stored with it (and the
        other way around).
        """
        vat = (record.get('cif') or '').replace(' ', '').replace('-', '').upper()
        if not vat:
            return
        candidates = {vat}
        if len(vat) > 2 and vat[:2].isalpha() and vat[2:]:
            candidates.add(vat[2:])  # captured with country prefix
        company_vals = self.company_id(record) or {}
        company_id = company_vals.get('company_id')
        country_code = False
        if company_id:
            country_code = self.env['res.company'].browse(company_id).country_id.code
        candidates.add((country_code or 'ES') + vat)  # partner stored with prefix
        domain = [('vat', 'in', list(candidates))]
        if company_id:
            domain.append(('company_id', 'in', [False, company_id]))
        partners = self.env['res.partner'].search(domain).mapped('commercial_partner_id')
        if len(partners) == 1:
            return {'vendor_id': partners.id}

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
            return {'okticket_remote_uri': record['remote_uri']}

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

        The actual PDF lives in ``signed_pdf_url`` (a pre-signed S3 URL). This
        brings that PDF into Odoo so it is available on the expense. Idempotent:
        it is not re-attached on later imports.
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

        required_fields = ['product_id', 'employee_id', 'company_id']

        filters, last_expenses_import = self.datetime_expenses_import_backend_filter(filters)
        only_reviewed = self.backend_record.import_only_reviewed_expenses

        for expense_ext_vals in backend_adapter.search(filters):
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
                    self._attach_ticket_image(binding, expense_ext_vals)
                    self._import_pdf_to_chatter(binding, expense_ext_vals)
                    _logger.info('Imported')

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

        _logger.info('Import from Okticket DONE')
        return okticket_hr_expense_ids

    def _attach_ticket_image(self, binding, record):
        """Attach the OkTicket ticket image to the expense chatter.

        The image lives in the chatter (and becomes the expense main
        attachment, shown in the native preview pane) instead of a binary
        field. Idempotent: skips if the attachment already exists.
        """
        remote_uri = record.get('remote_uri')
        if not remote_uri:
            return
        expense = binding.odoo_id
        extension = remote_uri.rsplit('.', 1)[-1] if '.' in remote_uri else 'jpg'
        att_name = 'OkTicket-%s.%s' % (record.get('_id'), extension)
        existing = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.expense'),
            ('res_id', '=', expense.id),
            ('name', '=', att_name),
        ], limit=1)
        if existing:
            return
        img_path = self.backend_record.image_base_url + remote_uri
        content = requests.get(img_path, timeout=30).content
        # Post in the backend language (schedulers run in en_US otherwise)
        lang = (self.backend_record.default_lang_id.code
                or expense.company_id.partner_id.lang
                or self.env.user.lang)
        expense = expense.with_context(lang=lang)
        expense.sudo().message_post(
            body=expense.env._('Ticket image imported from OkTicket'),
            attachments=[(att_name, content)],
        )

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
