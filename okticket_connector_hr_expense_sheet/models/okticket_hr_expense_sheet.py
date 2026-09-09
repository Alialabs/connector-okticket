# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import time

from odoo.addons.component.core import Component
from odoo.exceptions import UserError
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# Report names already taken in OkTicket, per (database, backend). OkTicket
# rejects a duplicated report name with a 422, and the exporter used to discover
# that by posting a candidate and reading the rejection -- one wasted write per
# collision, plus a warning in the log for something that is not a problem. The
# whole list costs a single call, so the free name is resolved locally instead.
#
# Same shape as the token cache in okticket_connector/components/backend_adapter:
# names are not transactional data, so sharing them beyond the current cursor is
# safe. Staleness costs at most one wasted POST, after which ``create`` drops the
# entry and the next lookup reloads.
_SHEET_NAME_CACHE = {}
# The set is only a shortcut, never the authority, so it can be held for a while.
SHEET_NAME_CACHE_TTL = 600


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.expense.sheet',
        inverse_name='odoo_id',
        string='Hr Expense Sheet Bindings')

    def _get_expense_sheet_okticket_id(self):
        for exp_sheet in self:
            external_ids = [ok_exp_sheet.external_id for ok_exp_sheet in exp_sheet.okticket_bind_ids]
            exp_sheet.okticket_expense_sheet_id = external_ids and external_ids[0] or '-1'

    def _set_expense_sheet_okticket_id(self):
        for exp_sheet in self.filtered(lambda sheet: sheet.okticket_bind_ids):
            exp_sheet.okticket_bind_ids.write({'external_id': exp_sheet.okticket_expense_sheet_id})

    def _search_expense_sheet_okticket_id(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, str):
            raise ValueError(_('Value should be string (not %s)'), value)
        odoo_ids = self.env['okticket.hr.expense.sheet'].search([
            ('external_id', operator, value)]).mapped('odoo_id').ids
        # Always a well-formed leaf: an empty domain makes the leaf vanish and
        # unbalances expression.parse() ("IndexError: pop from empty list")
        # whenever this field is combined with another one.
        return [('id', 'in', odoo_ids)]

    okticket_expense_sheet_id = fields.Char(string="OkTicket Expense_sheet_id",
                                            default='-1',
                                            compute=_get_expense_sheet_okticket_id,
                                            inverse=_set_expense_sheet_okticket_id,
                                            search=_search_expense_sheet_okticket_id)

    def export_record(self, *args, **kwargs):
        """ Creates a new expense sheet on Okticket """
        backend = self.env['okticket.backend'].search([('company_id', '=', self.company_id.id)], limit=1)
        # Call the export_record method with the backend and args
        self.env['okticket.hr.expense.sheet'].export_record(backend, self, *args)
        return True


class OkticketHrExpenseSheet(models.Model):
    _name = 'okticket.hr.expense.sheet'
    _description = 'Okticket Hr Expense Sheet'
    _inherit = 'okticket.binding'
    _inherits = {'hr.expense.sheet': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='hr.expense.sheet',
        string='Hr Expense Sheet',
        required=True,
        ondelete='cascade',
    )

    @api.model
    def export_expense_sheet(self, backend=False, filters=None, **kwargs):
        backend = backend or self.env['okticket.backend'].get_default_backend_okticket_connector()
        backend.ensure_one()
        if backend and backend.okticket_exp_sheet_sync:
            with backend.work_on(self._name) as work:
                importer = work.component(usage='importer')
                try:
                    importer.run(filters=filters)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise (e or UserError(_('Could not connect to Okticket')))

    def change_expense_sheet_status(self, expense_sheets, action_id, comments='No comment'):
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector(company=expense_sheets[0].company_id)
        backend.ensure_one()
        if backend and backend.okticket_exp_sheet_sync:
            with backend.work_on(self._name) as work:
                adapter = work.component(usage='backend.adapter')
                try:
                    return adapter.change_expense_sheet_status(expense_sheets, action_id, comments=comments)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise (e or UserError(_('Could not connect to Okticket')))

    def delete_expense_sheet(self, exp_sheet):
        """ Delete expense sheet in OkTicket related with Odoo hr.expense.sheet that is being unlinked"""
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector(company=exp_sheet.company_id)
        if backend and backend.okticket_exp_sheet_sync:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='record.exporter')
                try:
                    return exporter.delete_expense_sheet(exp_sheet)
                except Exception as e:
                    _logger.error('Exception: %s\n', e)
                    import traceback
                    traceback.print_exc()
                    raise Warning(_('Could not connect to Okticket'))
        else:
            _logger.warning('WARNING! NO EXISTE BACKEND PARA LA COMPANY %s (%s)\n',
                            self.env.user.company_id.name, self.env.user.company_id.id)

class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    okticket_hr_expense_sheet_ids = fields.One2many(
        comodel_name='okticket.hr.expense.sheet',
        inverse_name='backend_id',
        string='Hr Expense Sheet Bindings',
        context={'active_test': False})

    okticket_exp_sheet_sync = fields.Boolean(
        'Expense Sheets Synchronization',
        default=True
    )


class HrExpenseSheetAdapter(Component):
    _name = 'okticket.hr.expense.sheet.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.hr.expense.sheet'

    def _sheet_name_cache_key(self):
        return (self.env.cr.dbname, self.backend_record.id)

    def taken_sheet_names(self):
        """Names already used by a report of this backend's company.

        Loaded once and reused: the listing is one call for the whole company,
        against one wasted POST per collision the other way round.

        Never fails the export: if the listing cannot be read the caller simply
        gets an empty set and falls back to probing the API, which is exactly
        the previous behaviour.
        """
        key = self._sheet_name_cache_key()
        cached = _SHEET_NAME_CACHE.get(key)
        if cached and (time.monotonic() - cached['loaded_at']) < SHEET_NAME_CACHE_TTL:
            return cached['names']

        names = set()
        try:
            if self._auth():
                result = self.okticket_api.find_expense_sheet_names(
                    https=self.collection.https)
                rows = (result or {}).get('result') or []
                if isinstance(rows, dict):  # not paginated away for some reason
                    rows = rows.get('data') or []
                names = {row['name'] for row in rows
                         if isinstance(row, dict) and row.get('name')}
                _logger.info('Okticket: %s report names cached for backend %s',
                             len(names), self.backend_record.name)
        except Exception as exc:
            _logger.warning('Okticket: could not list report names for backend %s '
                            '(%s); falling back to probing names one by one',
                            self.backend_record.name, exc)
            return set()

        _SHEET_NAME_CACHE[key] = {'names': names, 'loaded_at': time.monotonic()}
        return names

    def remember_sheet_name(self, name):
        """Record a name just used, so two sheets of the same run cannot pick it."""
        cached = _SHEET_NAME_CACHE.get(self._sheet_name_cache_key())
        if cached and name:
            cached['names'].add(name)

    def invalidate_sheet_names(self):
        """Drop the cache after OkTicket disagreed with it."""
        _SHEET_NAME_CACHE.pop(self._sheet_name_cache_key(), None)

    def prepare_values(self, values):
        """
        Generates prepares valid values dictionary to create a expense sheet in Okticket from other one
        :param values: values dict
        :return: prepared values dict
        """
        return {
            'name': values.name,
            'user_id': values.employee_id.okticket_user_id,
            'company_id': values.company_id.okticket_company_id,
        }

    def create(self, values):
        if self._auth():
            try:
                result = self.create_expense_sheet(self.prepare_values(values))
            except UserError as e:
                # OkTicket rejects a report whose name is already in use with a
                # 422. That rejection used to be invisible (the 422 branch called
                # .json() on an http.client response and the AttributeError was
                # swallowed), which by accident returned a falsy value and made
                # the caller retry under another name. Now that the 422 is
                # reported properly it must be turned into that same falsy value
                # here: letting it propagate aborts -- and rolls back -- the whole
                # expense import over a single conflicting sheet name.
                msg = _('Could not create the Okticket expense sheet "%s": %s') % (
                    values.name, e)
                self.env['log.event'].add_event({
                    'backend_id': self.backend_record.id,
                    'type': 'warning',
                    'msg': msg,
                })
                _logger.warning(msg)
                # The cached name list disagreed with the server, so it is stale
                # (a report created elsewhere since it was read). Drop it: the
                # next lookup reloads and the fallback probing takes over here.
                self.invalidate_sheet_names()
                return False
            self.remember_sheet_name(values.name)
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return False

    def create_expense_sheet(self, values):
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/reports')
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json', }
        return okticketapi.general_request(url, "POST", fields_dict=values,
                                           headers=header, only_data=False, https=self.collection.https)

    def get_expenses_sheet(self, external_id):
        if self._auth():
            result = self.get_expenses_sheet_api(external_id)
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result['result']
        return False

    def get_expenses_sheet_api(self, external_id):
        """Every expense of an OkTicket report, following pagination.

        This used to ask with ``only_data=False``, which returns just the first
        page. With the documented per_page of 20, a report holding more expenses
        reported only 20 as linked, so the exporter treated all the others as
        missing and re-PATCHed them on every single write. ``only_data=True``
        walks ``links.next`` / ``meta.last_page`` and returns the flat list.
        """
        okticketapi = self.okticket_api
        path = '/reports/%s/expenses' % external_id
        url = okticketapi.get_full_path(path)
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json', }
        return okticketapi.general_request(url, "GET", fields_dict={},
                                           headers=header, only_data=True, https=self.collection.https)

    def unlink_expenses_sheet(self, external_ids_to_unlink):
        """
        Unlink Okticket expenses from expense sheets
        :param external_ids_to_unlink: external_id list char

        The unlink used to be issued *inside* the loop over a list that grew on
        every iteration, so expense 1 was patched N times, expense 2 N-1 times
        and so on: N(N+1)/2 PATCH calls for N expenses. A report holding a few
        hundred stale expenses turned that into hundreds of thousands of API
        calls. One pass, one batch.
        """
        if not external_ids_to_unlink:
            return True
        # Single query instead of one search per external id.
        bindings = self.env['okticket.hr.expense'].search(
            [('external_id', 'in', list(external_ids_to_unlink))])
        expenses_to_unlink = bindings.mapped('odoo_id')

        unknown_ids = set(external_ids_to_unlink) - set(bindings.mapped('external_id'))
        if unknown_ids:
            # These exist in the Okticket report but not in Odoo. Importing them
            # is not implemented; say so instead of dropping them silently.
            msg = _('Okticket expenses in the report with no Odoo counterpart, '
                    'left untouched: %s') % ', '.join(sorted(unknown_ids))
            self.env['log.event'].add_event({
                'backend_id': self.backend_record.id,
                'type': 'warning',
                'msg': msg,
            })
            _logger.warning(msg)

        if expenses_to_unlink:
            self.set_report_expense(False, expenses_to_unlink)
        return True

    def delete_expense_sheet(self, expense_sheet_id):
        if self._auth():
            result = self.okticket_api_delete_expense_sheet(expense_sheet_id)
            # Log event
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    # TODO: refactorizar este método para incluir en el connector y reutilizar por las operaciones de unlink
    def okticket_api_delete_expense_sheet(self, expense_sheet_id):
        # Esto en la api
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/reports')
        url = url + '/' + expense_sheet_id
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        return okticketapi.general_request(url, "DELETE", {},
                                           headers=header, only_data=False, https=self.collection.https)

    def link_expenses_sheet(self, sheet_external_id, expenses_to_link):
        """
        Adds error managing when it tries to link expenses to indicated expenses sheet
        and the expense sheet is in a not valid state
        :param sheet_external_id: Okticket external id of the expense sheet (char)
        :param expenses_to_link: hr.expense list to link to Okticket expense sheet
        """
        result = False
        try:
            result = self.set_report_expense(sheet_external_id, expenses_to_link)
        except UserError as error:
            # The report is discarded only when it would stay empty, which is
            # the case this branch was written for: a report just created for a
            # batch that OkTicket then refuses. It used to be deleted
            # unconditionally, so a report already holding every expense linked
            # in earlier runs was destroyed as soon as a later batch was refused
            # in full. Measured on the reference company: six reports of 144,
            # 124, 113, 105, 94 and 81 expenses deleted in one pass, because the
            # 70 records OkTicket answers 403 for were the whole batch of that
            # run. The binding went with them, leaving the sheets unlinked.
            expenses_in_report = self.get_expenses_sheet(sheet_external_id) or []
            if isinstance(expenses_in_report, dict):
                expenses_in_report = expenses_in_report.get('data') or []
            sheet = expenses_to_link[0].sheet_id if expenses_to_link else False
            msg = _('\nExpense sheet %(sheet)s (Odoo id %(sheet_id)s): none of the '
                    '%(total)s expenses of this run could be linked to OkTicket report '
                    '%(report)s. %(reason)s') % {
                'sheet': sheet and sheet.name or '-',
                'sheet_id': sheet and sheet.id or '-',
                'total': len(expenses_to_link),
                'report': sheet_external_id,
                'reason': error,
            }
            if expenses_in_report:
                msg += _(' The report is kept: it still holds %(held)s expenses linked in '
                         'earlier runs, and deleting it would remove them from OkTicket '
                         'too. The expenses of this run stay on the Odoo sheet with no '
                         'OkTicket counterpart, so the two sides differ for those lines.') % {
                    'held': len(expenses_in_report),
                }
            else:
                msg += _(' The report holds no expense and is deleted.')

            # 'error' and not 'warning': the sheet is left out of step with
            # OkTicket, which someone has to reconcile by hand.
            self.env['log.event'].add_event({
                'backend_id': self.backend_record.id,
                'type': 'error',
                'msg': msg,
            })
            _logger.error(msg)
            if expenses_in_report:
                # Truthy so the caller keeps the binding: the report is still
                # the sheet's report, and the expenses it holds are still linked.
                return True
            self.delete_expense_sheet(sheet_external_id)

        return result

    # def link_expenses_sheet(self, sheet_external_id, expenses_to_link):
    #     """
    #     Links expenses to indicated expenses sheet
    #     :param sheet_external_id: Okticket external id of the expense sheet (char)
    #     :param expenses_to_link: hr.expense list to link to Okticket expense sheet
    #     """
    #     return self.set_report_expense(sheet_external_id, expenses_to_link)

    def set_report_expense(self, report_id, expenses):
        """Link the expenses of a sheet to their OkTicket report, one by one.

        Each expense is attempted on its own. OkTicket refuses some of them with
        a 403 and an empty body -- old records it no longer serves through
        ``GET /expenses/{id}`` either, although they still come back in the
        listing -- and a single refusal used to propagate out of here, make
        ``link_expenses_sheet`` delete the report and leave *every* expense of
        the sheet without one. Measured on the reference company: 70 of the 102
        expenses older than the current year answer 403, and they dragged 431
        perfectly good ones down with them.

        A refused expense stays on the Odoo sheet and is reported in the
        connector log. Detaching it is deliberately not done: an expense with no
        sheet is the one state the destructive pre-import prune can delete, so
        that would trade a divergence someone can reconcile for silent data loss.

        :raise UserError: only when not a single expense could be linked. The
            caller then discards the report if -- and only if -- it would stay
            empty; a report already holding expenses is kept.
        """
        expense_backend_adapter = self.component(usage='backend.adapter', model_name='okticket.hr.expense')
        linked, refused = [], []
        for expense in expenses:
            expense_external_id = expense.okticket_bind_ids and expense.okticket_bind_ids[0].external_id or False
            if not expense_external_id:
                continue
            vals_dict = {
                'company_id': expense.company_id.okticket_company_id,
                'user_id': expense.employee_id.okticket_user_id,
                'report_id': report_id or "",
            }
            try:
                expense_backend_adapter.write_expense(expense_external_id, vals_dict)
                linked.append(expense)
            except Exception as exc:
                refused.append((expense, expense_external_id, exc))
                _logger.warning(
                    'OkTicket refused expense %s (OkTicket id %s) for report %s: %s',
                    expense.id, expense_external_id, report_id, exc)

        if refused and not linked:
            raise UserError(_(
                'OkTicket refused every expense of this sheet (%(total)s of them). '
                'First reason: %(reason)s') % {
                    'total': len(refused),
                    'reason': refused[0][2],
                })

        if refused:
            # One entry per sheet rather than per expense: a sheet can carry
            # dozens and the connector log has to stay readable.
            msg = _('Expense sheet report %(report)s: %(linked)s of %(total)s expenses '
                    'linked in OkTicket. The other %(refused)s were refused and stay on '
                    'the Odoo sheet without their OkTicket counterpart, so the two sides '
                    'differ for those lines. OkTicket ids: %(ids)s. First reason: '
                    '%(reason)s') % {
                'report': report_id,
                'linked': len(linked),
                'total': len(linked) + len(refused),
                'refused': len(refused),
                'ids': ', '.join(r[1] for r in refused[:10]) + ('...' if len(refused) > 10 else ''),
                'reason': refused[0][2],
            }
            self.env['log.event'].add_event({
                'backend_id': self.backend_record.id,
                'type': 'error',
                'msg': msg,
            })
            _logger.error(msg)
        return True

    def search(self, filters=False):
        if self._auth():
            if filters and filters.get('sheet_expense_external_id'):
                result = self.okticket_api.find_report_by_id(filters['sheet_expense_external_id'],
                                                             https=self.collection.https)
            else:
                result = self.okticket_api.find_expense_sheets(https=self.collection.https)
                if filters:
                    filter_result = []
                    for okticket_user in result.get('result', []):
                        valid_result = True
                        for filter_key, filter_val in filters.items():
                            if not filter_key in okticket_user \
                                    or okticket_user[filter_key] != filter_val:
                                valid_result = False
                                break
                        if valid_result:
                            filter_result.append(okticket_user)
                    result['result'] = filter_result
            result['log'].update({
                'backend_id': self.backend_record.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])

            # Si el resultado es un valor True / False (control de errores que no interrumpen ejecución, ej.: 422))
            if isinstance(result['result'], bool):
                return []

            return result['result']
        return []

    # Valid state transition for Okticket expenses sheets
    # key: status_id from expense sheet
    # values: valid action_id that could be apply in this state
    _STATUS_TRANSITIONS = {
        0: [347],               # Open -> ['Submit']
        34: [348, 349, 350],    # 'Submited' -> ['Reset (Draft) from submitted', 'Approve', 'Cancel from submitted']
        3: [354],               # 'Rejected' -> ['Reset (Draft) from rejected']
        5: [351, 352],          # 'Approved' -> ['Post (Registered)', 'Refuse from approved']
        35: [353],              # 'Posted' -> ['Paid']
        36: []                  # 'Paid' -> []
    }

    def change_expense_sheet_status(self, expense_sheets, action_id, comments='No comment'):
        """
        Changes Okticket expenses sheets state through sent action id and Odoo hr.expense.sheet
        :param expense: hr.expense.sheets RecordSet
        :param action_id: Okticket expenses sheet status_id (int)
        """
        expense_sheet_backend_adapter = self.component(usage='backend.adapter',
                                                       model_name='okticket.hr.expense.sheet')
        # Current Okticket expenses sheets state
        for sheet in expense_sheets:
            sheet_expense_external_id = sheet.okticket_bind_ids and sheet.okticket_bind_ids[0].external_id or False
            if not sheet_expense_external_id:
                self._report_status_divergence(
                    sheet, action_id,
                    _('the sheet has no OkTicket report bound to it'))
                continue
            filter = {
                'sheet_expense_external_id': sheet_expense_external_id,
            }
            current_expense_sheet_oktk = expense_sheet_backend_adapter.search(filters=filter)
            if not current_expense_sheet_oktk:
                self._report_status_divergence(
                    sheet, action_id,
                    _('OkTicket did not return the report %s') % sheet_expense_external_id)
                continue
            current_status_id = current_expense_sheet_oktk.get('status_id')
            # Checks if the action is valid
            if action_id in self._STATUS_TRANSITIONS.get(current_status_id, []):
                # Modify expenses sheet status
                expense_sheet_backend_adapter.workflow_expense_sheet(sheet_expense_external_id, action_id,
                                                                     comments=comments)
            else:
                self._report_status_divergence(
                    sheet, action_id,
                    _('OkTicket does not allow it from its current status %s')
                    % current_status_id)
        return True

    def _report_status_divergence(self, sheet, action_id, reason):
        """Record that an Odoo state change could not be pushed to OkTicket.

        Every one of the three ways this can happen used to be silent in the
        connector log: no binding and "report not returned" said nothing at all,
        and the disallowed transition only reached the Python log and the sheet
        chatter. Resetting a *posted* sheet to draft is the case that bites --
        Odoo allows it, ``_STATUS_TRANSITIONS`` defines nothing for status 35
        beyond paying, so Odoo went back to draft while OkTicket stayed posted
        with nothing recorded anywhere an operator looks.

        Closing the workflow gap needs the customer's real process (see INT-807
        of the integration plan); making the divergence visible does not, and is
        what this does.
        """
        msg = _('Expense sheet "%(sheet)s" is now "%(state)s" in Odoo but the '
                'status could not be sent to OkTicket (action %(action)s): '
                '%(reason)s. Both sides are out of sync until someone fixes it '
                'by hand.') % {
            'sheet': sheet.display_name,
            'state': sheet.state,
            'action': action_id,
            'reason': reason,
        }
        _logger.warning(msg)
        backend = sheet.okticket_bind_ids[:1].backend_id or \
            self.env['okticket.backend'].search(
                [('company_id', '=', sheet.company_id.id)], limit=1)
        if backend:
            self.env['log.event'].add_event({
                'backend_id': backend.id,
                'type': 'warning',
                'msg': msg,
            })
        sheet.message_post(
            body=msg,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

    def workflow_expense_sheet(self, sheet_expense_external_id, action_id, comments='No comment'):
        if self._auth():
            result = self.okticket_api_workflow_expense_sheet(sheet_expense_external_id, action_id, comments=comments)
            result['log'].update({
                'backend_id': self.collection.id,
                'type': result['log'].get('type') or 'success',
            })
            self.env['log.event'].add_event(result['log'])
            return result.get('result')
        return False

    def okticket_api_workflow_expense_sheet(self, sheet_expense_external_id, action_id, comments='No comment'):
        okticketapi = self.okticket_api
        url = okticketapi.get_full_path('/reports')
        url += '/%s/actions/%s' % (sheet_expense_external_id, action_id)
        header = {
            'Authorization': okticketapi.token_type + ' ' + okticketapi.access_token,
            'Content-Type': 'application/json',
        }
        body = {
            'comment': comments
        }
        return okticketapi.general_request(url, "POST", body, headers=header, only_data=False,
                                           https=self.collection.https)
