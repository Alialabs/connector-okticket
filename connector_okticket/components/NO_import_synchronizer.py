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

from collections import defaultdict

import logging
from odoo.addons.connector.unit import synchronizer
import odoo
from odoo import _
from ..backend import okticket
from odoo.addons.component.core import AbstractComponent
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OkticketImportSynchronizer(synchronizer.ImportSynchronizer):
    """ Base importer for Okticket """

    _model_name = 'okticket.hr.expense'

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.ConnectorEnvironment`
        """
        super(OkticketImportSynchronizer, self).__init__(environment)
        self.okticket_id = None
        self.updated_on = None
        self._okticket_cache = defaultdict(dict)
        environment._okticket_cache = self._okticket_cache

    def _get_okticket_data(self):
        """ Return the raw Okticket data for ``self.okticket_id`` in a dict
        """
        return self.backend_adapter.read(self.okticket_id)

    def _map_data(self):
        """
        Return an instance of
        :py:class:`~openerp.addons.connector.unit.mapper.MapRecord`
        """
        return self.mapper.map_record(self.okticket_record)

    def _get_binding_id(self):
        """Return the binding id from the okticket id"""
        return self.binder.to_openerp(self.okticket_id)

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data):
        """ Create the OpenERP record """
        model = self.session.env[self.model._name]
        binding = model.create(data)

        _logger.info(
            '%s %d created from Okticket %s',
            self.model._name, binding.id, self.okticket_id)

        return binding

    def _update_data(self, map_record, **kwargs):
        return map_record.values(**kwargs)

    def _update(self, binding_id, data):
        """Update an OpenERP record"""
        model = self.session.env[self.model._name]
        record = model.browse(binding_id)
        record.write(data)

        _logger.info(
            '%s %d updated from Okticket record %s',
            self.model._name, binding_id, self.okticket_id)

    def run(self, expense_vals, options=None):
        """ Run the synchronization

        :param expense_vals: dict con vals para mapeo de hr.expenses.expenses
        :param options: dict of parameters used by the synchronizer
        """


        self.okticket_id = expense_vals.get('_id')
        self.okticket_record = expense_vals
        # self.okticket_record = self._get_okticket_data()

        # # Case where the okticket record is not found in the backend.
        # if self.okticket_record is None:
        #     return

        binding_id = self._get_binding_id()

        map_record = self._map_data()
        # self.updated_on = map_record.values()['updated_on']

        if binding_id:
            record = self._update_data(map_record)
            self._update(binding_id, record)
        else:
            record = self._create_data(map_record)
            binding_id = self._create(record).id

        self.binder.bind(self.okticket_id, binding_id)


# @okticket
# class OkticketBatchImportSynchronizer(synchronizer.ImportSynchronizer):
#
#     _model_name = 'okticket.hr.expense.expense'
#
#     def run(self, filters=None, options=None):
#         """
#         Run the synchronization for all users, using the connector crons.
#         """
#
#         # TODO provisional: recupera todos los gastos
#         expenses_dict_list = self.backend_adapter.search(None, filters)
#
#         session = self.session
#         model_name = self._model_name
#         backend_id = self.backend_record.id
#
#         for expense_vals in expenses_dict_list:
#             import_record.delay(session, model_name, backend_id, expense_vals, options=options)


# OpenERP
# @job
# def import_batch(session, model_name, backend_id, filters=None, options=None):
#     """ Prepare a batch import of records from Okticket """
#     env = get_environment(session, model_name, backend_id)
#     importer = env.get_connector_unit(OkticketBatchImportSynchronizer)
#     importer.run(filters=filters, options=options)
#
# @job
# def import_record(session, model_name, backend_id, expense_vals, options=None):
#     """ Import a record from Okticket """
#     env = get_environment(session, model_name, backend_id)
#     importer = env.get_connector_unit(OkticketImportSynchronizer)
#     importer.run(expense_vals, options=options)
