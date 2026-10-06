# -*- coding:utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo.addons.component.core import Component

from odoo import _
from odoo import fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HrExpenseBatchImporter(Component):
    _inherit = 'okticket.expenses.batch.importer'

    ### Métodos que recopilan la relación entre el estado del campo y las funciones de clasificación ###
    def _grouping_configuration_dict(self):
        """
        Dict with key:
         -'expense_sheet_grouping_method' selected
        Values, tuple with:
         - expenses classification method
        """
        return {
            'analytic': 'analytic_classification_method',
        }

    def _time_grouping_configuration_dict(self):
        """
        Dict with key:
         -'expense_sheet_grouping_time' selected
        Values, tuple with:
         - expenses grouped by classification method based on interval time selected
        """
        return {
            'no_interval': 'expenses_by_no_interval_time_method',
        }

    ### Métodos para recuperar dinámicamente la función correspondiente al estado actual ###
    def get_expense_sheet_classification_method(self):
        """
        Return expenses classification method based on expense_sheet_grouping_method selected
        """
        grouping_method = self.backend_record.company_id.expense_sheet_grouping_method
        conf_dict = self._grouping_configuration_dict()
        classification_method = grouping_method in conf_dict and \
                                conf_dict[grouping_method] or False
        if hasattr(self, classification_method) and callable(getattr(self, classification_method)):
            return getattr(self, classification_method)
        raise NotImplementedError('Function %s is not implemented', classification_method)

    def get_expense_sheet_grouping_time_method(self):
        """
        Returns a method to group expenses by a specified time interval
        """
        grouping_method = self.backend_record.company_id.expense_sheet_grouping_time
        conf_dict = self._time_grouping_configuration_dict()
        time_method = grouping_method in conf_dict and conf_dict[grouping_method] or False
        if hasattr(self, time_method) and callable(getattr(self, time_method)):
            return getattr(self, time_method)
        raise NotImplementedError('Function %s is not implemented', time_method)

    def build_sheet_name_group_suffix(self, group_fields=None):
        if group_fields is None:
            group_fields = {}
        suffix_translations = {
            'own_account': _('Own Account'),
            'company_account': _('Company Account')
        }

        suffix = ''
        if 'payment_mode' in group_fields:
            payment_mode = group_fields['payment_mode']
            if payment_mode in suffix_translations:
                payment_mode = suffix_translations[payment_mode]
            suffix += ' | ' + payment_mode
        if 'name' in group_fields:
            name = group_fields['name']
            if name:
                suffix += ' | ' + name
        return suffix

    def _get_base_sheet_name(self, expense, group_fields=None):
        """
        Sheet name base for generic sheet grouping.
        """
        if group_fields is None:
            group_fields = {}
        employee_name = expense.employee_id.name if expense.employee_id else ""
        base_sheet_name = f"{employee_name}"
        if 'analytic_ids' in group_fields:
            analytic_ids = group_fields['analytic_ids']
            analytic_account_name = expense.analytic_account_id.name if expense.analytic_account_id else _("NO COST CENTER")
            base_sheet_name += f" | {analytic_account_name}"
        base_sheet_name += self.build_sheet_name_group_suffix(group_fields)
        return base_sheet_name

    ### Funciones de clasificación de gastos ###
    def analytic_classification_method(self, expense_ids):
        """
        Classifies expenses based on analytic account, payment mode and employee
        :param expense_ids: list of okticket expense ids
        :return Grouped expenses structure
        """
        grouped_expenses = [
            # Por cada expense se genera esta estructura donde las key de group_fields son campos de hr.expense.sheet
            # {
            #     'group_fields': {
            #         'employee_id': expense.employee_id and expense.employee_id.id,
            #         'payment_mode': expense.payment_mode,
            #         'analytic_ids': expense.analytic_account_id.id,
            #     },
            #     'expense': expense,
            #     'sheet_name': expense.analytic_account_id.name,
            # }
        ]
        for expense in self.env['hr.expense'].browse(expense_ids):
            group_fields = {
                'employee_id': expense.employee_id and expense.employee_id.id,
                'payment_mode': expense.payment_mode,
                'analytic_ids': expense.analytic_account_id and expense.analytic_account_id.id or False,
            }
            grouped_expenses.append({
                'group_fields': group_fields,
                'expense': expense,
                'sheet_name': self._get_base_sheet_name(expense, group_fields),
                'suffix': self.build_sheet_name_group_suffix(group_fields)
            })
        return grouped_expenses

    ### Funciones de clasificación de gastos por intervalo temporal ###
    def expenses_by_no_interval_time_method(self, grouped_expenses):
        """
        No action needed
        """
        return grouped_expenses

    ### Funciones de clasificación de gastos por intervalo temporal ###
    def grouped_expenses_managing(self, grouped_expenses):
        """
        Creates/updates hr.expense.sheet based on grouped_expenses data classification.
        :param grouped_expenses: list of dict with 'group_fields' dict with key hr.expense.sheet field and value
        """
        hr_expense_sheet_obj = self.env['hr.expense.sheet']

        for expense_data in self._batch_grouped_expenses(grouped_expenses):
            # One unusable sheet must not abort the whole import. Creating a sheet
            # pushes it to OkTicket, so anything from a duplicated report name to a
            # network error used to propagate all the way up and roll back every
            # expense imported in this run -- the expenses were already in Odoo but
            # the transaction was discarded, so nothing arrived.
            try:
                with self.env.cr.savepoint():
                    self._manage_grouped_expense(hr_expense_sheet_obj, expense_data)
            except Exception as e:
                msg = _('Could not build the expense sheet for expenses %s: %s') % (
                    expense_data['expenses'].ids, e)
                self.env['log.event'].add_event({
                    'backend_id': self.backend_record.id,
                    'type': 'error',
                    'msg': msg,
                })
                _logger.error(msg)

        return grouped_expenses

    def _batch_grouped_expenses(self, grouped_expenses):
        """Merge the per-expense entries that end up on the same expense sheet.

        The classification methods emit one entry per expense, and each entry used
        to issue its own ``write`` on the sheet. Every write fires
        ``on_record_write``, which re-exports the whole sheet and re-PATCHes every
        expense already linked to it, so filling a sheet with N expenses cost
        O(N^2) API calls -- a report with 97 expenses meant around 3000 PATCH
        calls where 97 suffice. Grouping first means one write, and therefore one
        export, per sheet.

        The key is the grouping fields plus the sheet name, so the methods that
        deliberately produce one sheet per expense (``single_expense``, which puts
        the expense name in the key) keep doing exactly that.
        """
        batches = {}
        for index, expense_data in enumerate(grouped_expenses):
            group_fields = expense_data.get('group_fields') or {}
            # repr() keeps the key hashable whatever the classification method put
            # in the grouping fields (ids, selection values, dates, False).
            key = (
                tuple(sorted((field, repr(value)) for field, value in group_fields.items())),
                repr(expense_data.get('sheet_name')),
            )
            if 'name' in group_fields:
                # ``single_expense`` grouping: the expense's own name is part of the
                # key, so every entry is meant to get its own sheet -- including two
                # expenses that share employee, payment mode *and* name, which the
                # demo data does contain. Merging them would silently turn N sheets
                # into fewer, so those entries are never batched together.
                key = key + (index,)
            batch = batches.get(key)
            if batch is None:
                batch = dict(expense_data)
                batch['expenses'] = self.env['hr.expense'].browse()
                batches[key] = batch
            if expense_data.get('expense'):
                batch['expenses'] |= expense_data['expense']
        return list(batches.values())

    def _manage_grouped_expense(self, hr_expense_sheet_obj, expense_data):
        """Create or update the hr.expense.sheet for a batch of grouped expenses."""
        # Construye el dominio de búsqueda para la hoja de gastos
        sheet_domain = [('state', 'in', ['draft'])]
        for sheet_field, sheet_value in expense_data['group_fields'].items():
            if sheet_field != 'analytic_ids' or sheet_value:
                # Si el campo no es 'analytic_ids' o si lo es pero tiene un valor, añadir al dominio
                sheet_domain.append((sheet_field, '=', sheet_value))
            else:
                # Si no hay cuenta analítica, usar 'IS NULL'
                sheet_domain.append(('analytic_ids', '=', False))

        # Valores a actualizar/crear en la hoja de gastos
        # Un solo comando por hoja: el listener de export se dispara una vez.
        expenses = expense_data.get('expenses')
        if expenses is None:  # llamada directa con una única expense
            expenses = expense_data['expense']
        expense_sheet_values = {
            'expense_line_ids': [(4, expense_id) for expense_id in expenses.ids],
        }

        # Busca si ya existe una hoja de gastos con el dominio especificado
        hr_expense_sheet = hr_expense_sheet_obj.search(sheet_domain)

        if hr_expense_sheet:  # Actualiza la hoja existente
            hr_expense_sheet.write(expense_sheet_values)
            return

        # Crea una nueva hoja de gastos
        new_sheet_values = {}
        for sheet_field, sheet_value in expense_data['group_fields'].items():
            if sheet_field not in new_sheet_values:
                new_sheet_values[sheet_field] = sheet_value

        # Agrega el nombre de la hoja si está disponible
        if 'sheet_name' in expense_data and expense_data['sheet_name']:
            new_sheet_values['name'] = expense_data['sheet_name']

        # Prepara y actualiza los valores de la nueva hoja de gastos
        new_sheet_values = hr_expense_sheet_obj.prepare_expense_sheet_values(new_sheet_values)
        new_sheet_values.update(expense_sheet_values)

        new_sheet = hr_expense_sheet_obj.create(new_sheet_values)

        # Manejo de errores durante la sincronización con Okticket
        if new_sheet and not new_sheet.okticket_bind_ids \
                and self.collection.okticket_exp_sheet_sync:
            new_sheet.unlink()  # Elimina la hoja de gastos si ocurre un error

    def sanitize_expenses(self, hr_expense_ids):
        """
        Checks which expenses are not related with a expense sheet.
        :param hr_expense_ids: list of int (expense ids)
        :return: list of expense ids
        """
        return self.env['hr.expense'].browse(hr_expense_ids).filtered(lambda x: not x.sheet_id).ids

    ### Función de importación de gastos ###
    def run(self, filters=None, options=None):
        """
        Imports expenses from Okticket and it classify them in expense sheets
        """
        okticket_hr_expense_ids = super(HrExpenseBatchImporter, self).run(filters=filters, options=options)

        # TODO - Ver si es viable de pasar por parámetro el object expense
        # Recupera hr.expenses relacionados con los gastos de okticket. Solo aquellos con cuenta anlítica
        hr_expense_ids = [rel.odoo_id.id for rel in self.env['okticket.hr.expense'].search([
            ('id', 'in', okticket_hr_expense_ids)])]

        hr_expense_ids = self.sanitize_expenses(hr_expense_ids)
        self.expense_sheet_processing(hr_expense_ids)

        self.env.cr.commit()  # Fin de proceso de backend

        return okticket_hr_expense_ids

    ### Función donde se recuperan dinámicamente las funciones de
    # clasificación, división por intervalo temporal y agrupación en hojas de gastos de gastos ###
    def expense_sheet_processing(self, hr_expense_ids):
        """
        Expense classification and expense sheet creation/modification based on
        grouping method and time interval selected in current company
        :param hr_expense_ids: list of int (hr.expense ids)
        """
        # 1º) Clasificación de gastos en base al método de agrupación indicado
        # Retorna una estructura de datos que el método de gestión de hojas de gasto es capaz de manejar
        expense_classification_method = self.get_expense_sheet_classification_method()
        grouped_expenses = expense_classification_method(hr_expense_ids)

        # 2º) Reclasificación en base a parámetros temporales
        expense_time_interval_method = self.get_expense_sheet_grouping_time_method()
        grouped_expenses = expense_time_interval_method(grouped_expenses)
        grouped_expenses = self.assign_company_to_expenses(grouped_expenses)

        # 3º) Creación/actualización de hojas de gasto
        self.grouped_expenses_managing(grouped_expenses)

        return True

    def assign_company_to_expenses(self, grouped_expenses):
        # Asegurarse de iterar sobre cada elemento en la lista grouped_expenses
        for expense_group in grouped_expenses:
            # Actualizar el diccionario group_fields en cada elemento
            expense_group['group_fields'].update({
                'company_id': self.backend_record.company_id.id,
            })
        return grouped_expenses


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def delete_expense_sheet(self):
        """Delete related expense sheet in Okticket"""
        self.env['okticket.hr.expense.sheet'].sudo().delete_expense_sheet(self)
        return True

    def _search_analytic_ids(self, operator, value):
        if not isinstance(value, list):
            value = [value]

        # Si el valor es False, significa que estamos buscando registros donde analytic_account_id es NULL
        if value == [False] or value == [None]:
            self.env.cr.execute("""
                SELECT DISTINCT sheet.id
                FROM hr_expense_sheet sheet
                INNER JOIN hr_expense exp
                ON sheet.id = exp.sheet_id
                WHERE exp.analytic_account_id IS NULL
            """)
        else:
            self.env.cr.execute("""
                SELECT DISTINCT sheet.id
                FROM hr_expense_sheet sheet
                INNER JOIN hr_expense exp
                ON sheet.id = exp.sheet_id
                WHERE exp.analytic_account_id IN %s
            """, (tuple(value),))

        return [('id', 'in', [sheet_id[0] for sheet_id in self.env.cr.fetchall()])]

    analytic_ids = fields.Many2many('account.analytic.account',
                                    string='Analytic account',
                                    readonly=True,
                                    compute='_compute_analytic_ids',
                                    search="_search_analytic_ids")

    @api.depends('expense_line_ids')
    def _compute_analytic_ids(self):
        for sheet in self:
            sheet.analytic_ids = sheet.expense_line_ids.mapped('analytic_account_id').ids

    def check_empty_sheet(self):
        """
        If sheet is empty, delete it
        """
        self.filtered(lambda x: not x.expense_line_ids).unlink()

    def write(self, vals):
        """
        Removes empty expense sheets
        """
        result = super(HrExpenseSheet, self).write(vals)
        # In 16.0 the state is a plain field that every path writes -- the
        # buttons, the duplicate-expense and refusal wizards, the payment
        # wizard, ``set_to_paid``, cancelling or reversing the entry -- so this
        # is the one place every change goes through.
        if vals and 'state' in vals:
            self._okticket_queue_status_sync()
        if vals and 'expense_line_ids' in vals:
            self.check_empty_sheet()
        return result

    def prepare_expense_sheet_values(self, raw_values):
        sale_order = False
        complete_name = raw_values and 'name' in raw_values and raw_values['name'] or False
        analytic = 'analytic_ids' in raw_values and raw_values['analytic_ids'] and \
                   self.env['account.analytic.account'].browse(raw_values['analytic_ids'])

        # Obtención de sale.order para el user
        if analytic:
            sale_order = analytic.get_related_sale_order()

        # Si no se tiene un nombre para la hoja de gasto, se busca en la cuenta analítica y el sale.order si existen
        if not complete_name and analytic:
            if sale_order and sale_order.partner_id and sale_order.partner_id.name:
                complete_name = '-'.join([sale_order.partner_id.name, analytic.name])
            else:
                complete_name = analytic.name  # Sin cliente

        raw_values.update({
            'name': complete_name or 'NO-NAME-EXP-SHEET',  # En última instancia (no debería de ejecutarse nunca
            'employee_id': raw_values['employee_id'],
            'user_id': sale_order and sale_order.user_id and sale_order.user_id.id or False,
            'payment_mode': raw_values['payment_mode'],
            'company_id': raw_values['company_id']
        })
        return raw_values

    # --------------------------------------------
    # OkTicket report status follows the Odoo state
    # --------------------------------------------
    _OKTICKET_STATUS_SYNC_KEY = 'okticket_sheet_status_sync'

    def _okticket_status_sync_queue(self):
        """This transaction's pending status sync, registered on first use.

        Kept in ``cr.precommit.data`` and run as a precommit callback, so every
        state change of the transaction -- whichever button, wizard or
        accounting operation caused it -- is pushed once, after Odoo is done,
        and only if the transaction is about to commit.
        """
        data = self.env.cr.precommit.data
        queue = data.get(self._OKTICKET_STATUS_SYNC_KEY)
        if queue is None:
            queue = data[self._OKTICKET_STATUS_SYNC_KEY] = {'ids': set(), 'comments': {}}
            self.env.cr.precommit.add(self.browse()._okticket_run_status_sync)
        return queue

    def _okticket_queue_status_sync(self):
        """Queue the sheets whose OkTicket report has to follow their state.

        Only saved sheets that already have a report: a sheet being created gets
        its report from the exporter, already open, and a sheet typed in Odoo
        has nothing to follow.
        """
        # Not while modules load: a recompute triggered by an upgrade is not a
        # state change anybody made.
        if self.env.context.get('okticket_no_status_sync') or not self.env.registry.ready:
            return
        sheets = self.filtered(lambda sheet: isinstance(sheet.id, int) and sheet.okticket_bind_ids)
        if sheets:
            self._okticket_status_sync_queue()['ids'].update(sheets.ids)

    def _okticket_run_status_sync(self):
        queue = self.env.cr.precommit.data.pop(self._OKTICKET_STATUS_SYNC_KEY, None)
        if not queue or not queue['ids']:
            return
        sheets = self.browse(sorted(queue['ids'])).exists()
        if sheets:
            self.env['okticket.hr.expense.sheet'].sync_expense_sheet_status(
                sheets, comments=queue['comments'])
            # Precommit callbacks run after the ORM flush: the log entries and
            # chatter messages written while syncing need one of their own.
            self.env.flush_all()

    def refuse_sheet(self, reason):
        """Keep the refusal reason, sent to OkTicket as the action's comment."""
        if not self.env.context.get('okticket_no_status_sync'):
            comments = self._okticket_status_sync_queue()['comments']
            for sheet in self:
                comments[sheet.id] = reason
        return super().refuse_sheet(reason)

    def unlink(self):
        return super(HrExpenseSheet, self).unlink()
