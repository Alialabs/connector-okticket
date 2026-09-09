import logging
from odoo import _, models, fields, api
from odoo.exceptions import UserError
from odoo.addons.component.core import AbstractComponent

_logger = logging.getLogger(__name__)


class OkticketBinding(models.AbstractModel):
    """ Abstract Model for the Bindings.
    All the models used as bindings between Okticket and Odoo should
    ``_inherit`` it.
    """

    _name = 'okticket.binding'
    _inherit = 'external.binding'
    _description = 'Okticket Binding (abstract)'

    # FYI: odoo_id = odoo-side id must be declared in concrete model
    backend_id = fields.Many2one(
        comodel_name='okticket.backend',
        string='Okticket Backend',
        required=True,
        ondelete='restrict',
    )
    external_id = fields.Char(string='ID on Okticket')

    _sql_constraints = [
        ('okticket_uniq', 'unique(backend_id, external_id)',
         'A binding already exists with the same Okticket ID.'),
    ]

    @api.model
    def import_batch(self, backend, filters=None, **kwargs):
        """ Prepares a batch import of records from OkTicket """
        if not backend:
            # No backend configured (e.g. employee created in a company
            # without Okticket backend): nothing to import
            _logger.warning('No Okticket backend available, skipping batch import of %s', self._name)
            return
        backend.ensure_one()
        filters = filters or {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage='importer')
            try:
                importer.run(filters=filters)
            except Exception as e:
                _logger.error('Exception: %s\n', e)
                import traceback
                traceback.print_exc()
                raise (e or UserError(_('Could not connect to Okticket')))

    @api.model
    def import_record(self, backend, filters=False):
        """ Imports Okticket record """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(filters=filters)

    def export_record(self, backend, *args):
        """ Exports record on OkTicket """
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(*args)
