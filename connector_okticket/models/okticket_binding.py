# -*- coding: utf-8 -*-
#
#    Created on 16/04/19
#
#    @author:alia
#
#
# 2019 ALIA Technologies
#       http://www.alialabs.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from odoo import _
from odoo import models, fields, api
from odoo.addons.queue_job.job import job
from odoo.addons.component.core import AbstractComponent
import logging

_logger = logging.getLogger(__name__)

class OkticketBinding(models.AbstractModel):
    """ Abstract Model for the Bindings.
    All the models used as bindings between Okticket and Odoo should
    ``_inherit`` it.
    """

    _name = 'okticket.binding'
    _inherit = 'external.binding'
    _description = 'Okticket Binding (abstract)'

    # odoo_id = odoo-side id must be declared in concrete model
    backend_id = fields.Many2one(
        comodel_name='okticket.backend',
        string='Okticket Backend',
        required=True,
        ondelete='restrict',
    )
    # fields.Char because 0 is a valid Okticket ID
    external_id = fields.Char(string='ID on Okticket')

    _sql_constraints = [
        ('okticket_uniq', 'unique(backend_id, external_id)',
         'A binding already exists with the same Okticket ID.'),
    ]


    @job
    @api.model
    def import_batch(self, backend, filters=None, **kwargs):
        """ Prepare a batch import of records from OkTicket """
        backend.ensure_one()
        if filters is None:
            filters = {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage='importer')
            try:
                importer.run(filters=filters)
            except Exception as e:
                _logger.error('Exception: %s\n', e)
                import traceback
                traceback.print_exc()
                raise Warning(_('Could not connect to Okticket'))

    @job
    @api.model
    def import_record(self, backend, filters=False):
        """ Import a Okticket record """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(filters=filters)

    @job(default_channel='root.magento')
    # @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_record(self, *args):
        """ Export a record on OkTicket """
        backend = self.env['okticket.backend'].get_default_backend_okticket_connector()
        backend.ensure_one()
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            # obj_vals = kwargs and kwargs.get('obj_vals') or False
            return exporter.run(*args) # le pasa el binding??
        

class OkticketBinder(AbstractComponent):
    _name = 'okticket.binder'
    _inherit = ['base.binder', 'base.okticket.connector']
    _description = 'Okticket Binder'

    backend_id = fields.Many2one(
        'okticket.backend', 'Okticket Backend', required=True,
        ondelete='restrict'
    )
    okticket_id = fields.Char('ID in Okticket', required=True)


    _sql_constraints = [
        ('okticket_uniq', 'unique(backend_id, okticket_id)',
         'A record with same ID on OkTicket already exists.'),
    ]




