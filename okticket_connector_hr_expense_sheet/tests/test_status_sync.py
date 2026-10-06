# Copyright 2026 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.okticket_connector_hr_expense_sheet.models.okticket_hr_expense_sheet import (
    HrExpenseSheetAdapter,
)


class FakeOkticket:
    """OkTicket reports as a status machine, with the same rules as the API.

    An action the report's status does not allow raises, exactly as the real
    API refuses it, so a test fails if the connector ever sends one.
    """

    def __init__(self):
        self.status = {}
        self.calls = []
        self.accounted = []

    def search(self, adapter, filters=False):
        report_id = filters['sheet_expense_external_id']
        return {'_id': report_id, 'status_id': self.status[report_id]}

    def workflow(self, adapter, report_id, action_id, comments='No comment'):
        current = self.status[report_id]
        if action_id not in HrExpenseSheetAdapter._STATUS_TRANSITIONS[current]:
            raise AssertionError('action %s not allowed from %s' % (action_id, current))
        self.calls.append((report_id, action_id, comments))
        self.status[report_id] = HrExpenseSheetAdapter._ACTION_TARGET_STATUS[action_id]
        return True

    def set_accounted(self, expense, new_state=True):
        self.accounted.append((expense.id, new_state))


@tagged('post_install', '-at_install')
class TestSheetStatusSync(TransactionCase):
    """The OkTicket report follows the state the Odoo sheet ends up in."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # One backend per company: reuse the database's own when there is one.
        Backend = cls.env['okticket.backend'].with_context(active_test=False)
        cls.backend = Backend.search([('company_id', '=', cls.company.id)], limit=1)
        if not cls.backend:
            cls.backend = Backend.create({
                'name': 'Backend de hojas',
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
        cls.backend.write({'active': True, 'okticket_exp_sheet_sync': True})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Empleada de hojas',
            'work_email': 'empleada.hojas@example.com',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Gasto de hojas',
            'can_be_expensed': True,
            'supplier_taxes_id': [(5, 0, 0)],
        })
        cls.counter = 0

    def setUp(self):
        super().setUp()
        self.okticket = FakeOkticket()
        fake = self.okticket
        patches = [
            patch.object(HrExpenseSheetAdapter, 'search',
                         lambda adapter, filters=False: fake.search(adapter, filters)),
            patch.object(HrExpenseSheetAdapter, 'workflow_expense_sheet',
                         lambda adapter, rid, action, comments='No comment':
                         fake.workflow(adapter, rid, action, comments)),
            patch.object(type(self.env['hr.expense']), '_okticket_accounted_expense',
                         lambda expense, new_state=True: fake.set_accounted(expense, new_state)),
        ]
        for one in patches:
            one.start()
            self.addCleanup(one.stop)

    # ------------------------------------------------------------------
    def _sheet(self, amount=10.0, date='2026-01-15', status=0, payment_mode='own_account'):
        TestSheetStatusSync.counter += 1
        expense = self.env['hr.expense'].create({
            'name': 'Ticket %s' % self.counter,
            'employee_id': self.employee.id,
            'product_id': self.product.id,
            'total_amount_currency': amount,
            'date': date,
            'payment_mode': payment_mode,
        })
        sheet = self.env['hr.expense.sheet'].create({
            'name': 'Hoja %s' % self.counter,
            'employee_id': self.employee.id,
            'expense_line_ids': [(6, 0, expense.ids)],
        })
        report_id = 'report-%s' % self.counter
        self.env['okticket.hr.expense.sheet'].create({
            'backend_id': self.backend.id,
            'odoo_id': sheet.id,
            'external_id': report_id,
        })
        self.okticket.status[report_id] = status
        self._commit()  # the creation itself pushes nothing
        self.okticket.calls.clear()
        self.okticket.accounted.clear()
        return sheet

    def _commit(self):
        """What a real commit does: flush, then run the precommit hooks."""
        self.env.flush_all()
        self.env.cr.precommit.run()

    def _actions(self):
        return [action for _report, action, _comment in self.okticket.calls]

    def _warnings(self):
        return self.env['log.event'].search_count(
            [('backend_id', '=', self.backend.id), ('type', '=', 'warning')])

    # ------------------------------------------------------------------
    def test_submit_sends_347_and_marks_the_expenses_accounted(self):
        sheet = self._sheet()
        sheet.action_submit_sheet()
        self._commit()
        self.assertEqual(self._actions(), [347])
        self.assertEqual(self.okticket.accounted, [(sheet.expense_line_ids.id, True)])

    def test_approve_with_a_duplicate_opens_the_wizard_and_sends_nothing(self):
        approved = self._sheet(amount=57.75, date='2026-02-01')
        approved.action_submit_sheet()
        approved.action_approve_expense_sheets()
        self._commit()
        duplicate = self._sheet(amount=57.75, date='2026-02-01')
        duplicate.action_submit_sheet()
        self._commit()
        self.okticket.calls.clear()

        action = duplicate.action_approve_expense_sheets()
        self._commit()
        self.assertEqual(action['res_model'], 'hr.expense.approve.duplicate')
        self.assertEqual(duplicate.state, 'submit')
        self.assertEqual(self._actions(), [])

        # Confirming the wizard approves, and only then OkTicket hears of it.
        wizard = self.env['hr.expense.approve.duplicate'].with_context(
            action['context']).create({})
        wizard.action_approve()
        self._commit()
        self.assertEqual(duplicate.state, 'approve')
        self.assertEqual(self._actions(), [349])

    def test_a_report_already_there_gets_no_call_and_no_warning(self):
        """The sheets the old behaviour left behind fix themselves."""
        sheet = self._sheet()
        sheet.action_submit_sheet()
        self._commit()
        self.okticket.calls.clear()
        self.okticket.status[sheet.okticket_bind_ids.external_id] = 5
        before = self._warnings()
        sheet.action_approve_expense_sheets()
        self._commit()
        self.assertEqual(self._actions(), [])
        self.assertEqual(self._warnings(), before)

    def test_approved_back_to_draft_goes_through_rejected(self):
        sheet = self._sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        self._commit()
        self.okticket.calls.clear()
        self.okticket.accounted.clear()
        sheet.action_reset_expense_sheets()
        self._commit()
        self.assertEqual(sheet.state, 'draft')
        self.assertEqual(self._actions(), [352, 354])
        self.assertEqual(self.okticket.accounted, [(sheet.expense_line_ids.id, False)])

    def test_refusal_reason_travels_as_the_comment(self):
        sheet = self._sheet()
        sheet.action_submit_sheet()
        self._commit()
        self.okticket.calls.clear()
        sheet._do_refuse('Falta el ticket')
        self._commit()
        self.assertEqual(self.okticket.calls[-1][1:], (350, 'Falta el ticket'))

    def test_several_sheets_at_once(self):
        """The list view approves many: no singleton read may break it."""
        sheets = self._sheet(amount=11) | self._sheet(amount=12)
        sheets.action_submit_sheet()
        sheets.action_approve_expense_sheets()
        self._commit()
        self.assertEqual(sorted(self._actions()), [347, 347, 349, 349])

    def test_posted_and_reopened_is_allowed_and_warned(self):
        sheet = self._sheet(amount=13)
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_create()
        self._commit()
        self.assertEqual(sheet.state, 'post')
        self.assertEqual(self._actions(), [347, 349, 351])
        before = self._warnings()
        sheet.action_reset_expense_sheets()
        self._commit()
        self.assertEqual(sheet.state, 'draft')
        self.assertEqual(self._actions(), [347, 349, 351])
        self.assertEqual(self._warnings(), before + 1)

    def test_payment_outside_any_button_still_reaches_okticket(self):
        sheet = self._sheet(amount=14)
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_create()
        self._commit()
        self.okticket.calls.clear()
        sheet.set_to_paid()
        self._commit()
        self.assertEqual(sheet.state, 'done')
        self.assertEqual(self._actions(), [353])

    def test_without_backend_sync_nothing_is_sent_nor_blocked(self):
        sheet = self._sheet(amount=15)
        self.backend.okticket_exp_sheet_sync = False
        sheet.action_submit_sheet()
        self._commit()
        self.assertEqual(sheet.state, 'submit')
        self.assertEqual(self._actions(), [])

    def test_status_path(self):
        path = HrExpenseSheetAdapter._status_path
        self.assertEqual(path(0, 36), [347, 349, 351, 353])
        self.assertEqual(path(3, 34), [354, 347])
        self.assertEqual(path(5, 5), [])
        self.assertIsNone(path(35, 0))
        self.assertIsNone(path(36, 5))
