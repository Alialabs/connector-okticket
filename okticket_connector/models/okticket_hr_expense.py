from odoo import fields, models, _
from odoo.addons.component.core import Component

# Fields asked for when listing expenses. The list matters for one reason: the
# API answers HTTP 500 while serialising ``review`` on at least one record of
# the reference company, and since a listing without ``fields`` returns every
# field, any wide listing died halfway through. Reproducible with
# ``updated_after=2000-01-01T00:00:00&limit=1&page=729``: 500 as it stands, 200
# with any ``fields`` set that leaves ``review`` out, 500 again as soon as it is
# added back. Everything the connector maps is here; ``review`` is added only
# when the backend actually filters by it.
EXPENSE_LIST_FIELDS = (
    '_id,id,amount,currency,rate,rate_amount,rate_datetime,rate_source,date,'
    'type_id,category_id,user_id,company_id,status_id,accounted,taxes,cif,name,'
    'comments,custom_fields,report_id,remote_uri,remote_path,local_path,'
    'signed_pdf_url,image_source,source,ticket_num,cost_center_id,department_id,'
    'card_id,payment_method,payment_method_id,tax_model_id,country_code,ocr,'
    'integrity_hash,app_version,created_at,created_by,updated_at,deleted_at'
)


class HrExpense(models.Model):
    _inherit = 'hr.expense'
    _description = 'HR Expense'

    okticket_bind_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='odoo_id',
        string='OkTicket Expense Bindings'
    )

    okticket_expense_id = fields.Char(
        string="OkTicket ID",
        compute='_compute_okticket_expense_id',
        inverse='_inverse_okticket_expense_id',
        search='_search_okticket_expense_id'
    )

    def _compute_okticket_expense_id(self):
        for expense in self:
            expense.okticket_expense_id = (
                expense.okticket_bind_ids[0].external_id if expense.okticket_bind_ids else '-1'
            )

    def _inverse_okticket_expense_id(self):
        for exp in self.filtered(lambda ex: ex.okticket_bind_ids):
            exp.okticket_bind_ids.write({'external_id': exp.okticket_expense_id})

    def _search_okticket_expense_id(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, str):
            raise ValueError(_('Value should be string (not %s)') % type(value).__name__)

        odoo_ids = self.env['okticket.hr.expense'].search([('external_id', operator, value)]).mapped('odoo_id').ids
        # Always a well-formed leaf: an empty domain makes the leaf vanish and
        # unbalances expression.parse() ("IndexError: pop from empty list")
        # whenever this field is combined with another one.
        return [('id', 'in', odoo_ids)]


class OkticketExpense(models.Model):
    _name = 'okticket.hr.expense'
    _description = 'Okticket HR Expense Binding'

    _inherit = 'okticket.binding'
    _inherits = {'hr.expense': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='hr.expense',
        string='Expense',
        required=True,
        ondelete='cascade'
    )

    def import_expenses_since(self, backend, since_date=None, **kwargs):
        # Reasignar el contexto para incluir la compañía
        self = self.with_company(self.backend_record.company_id)

        # Llamar al método import_batch con el contexto actualizado
        self.env['okticket.hr.expense'].sudo().with_context(company_id=backend.company_id.id).import_batch(backend,
                                                                                                           priority=5)
        return True


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    okticket_hr_expense_ids = fields.One2many(
        comodel_name='okticket.hr.expense',
        inverse_name='backend_id',
        string='HR Expense Bindings',
        context={'active_test': False}
    )


class ExpensesAdapter(Component):
    """
    Expenses Backend Adapter for Okticket

    Expenses in Okticket cannot be queried by the date of creation
    or update. The alternative is to search for all entries for a
    period of time and then filter these by the field updated_on.
    """
    _name = 'okticket.expense.adapter'
    _inherit = 'okticket.adapter'
    _usage = 'backend.adapter'
    _collection = 'okticket.backend'
    _apply_on = 'okticket.hr.expense'

    def search(self, filters=False):
        if not self._auth():
            return []

        params_dict = {
            'accounted': 'false',
            'statuses': '0,1,2',
            'fields': EXPENSE_LIST_FIELDS,
        }
        if self.backend_record.import_only_reviewed_expenses:
            # Needed to honour the option, and it is the field that makes the
            # API answer 500, so it is only requested when it is actually read.
            params_dict['fields'] += ',review'

        if filters and 'params' in filters and isinstance(filters['params'], dict):
            params_dict.update(filters['params'])

        if filters and filters.get('expense_external_id'):
            result = self.okticket_api.find_expense_by_id(
                filters['expense_external_id'], https=self.collection.https
            )
        else:
            result = self.okticket_api.find_expenses(
                params=params_dict, https=self.collection.https
            )

        result['log'].update({
            'backend_id': self.backend_record.id,
            'type': result['log'].get('type') or 'success',
        })
        self.env['log.event'].add_event(result['log'])

        if isinstance(result['result'], bool):
            return []

        return result['result']

    def last_listing_was_truncated(self):
        """Whether the last listing stopped on an error instead of its end.

        The importer needs this before advancing ``import_expenses_since``: a
        truncated listing that still moves the watermark forward leaves the
        records it never fetched behind the cut-off, and they never enter the
        incremental window again.
        """
        api = getattr(self, 'okticket_api', None)
        return bool(api is not None and getattr(api, 'last_listing_truncated', False))
