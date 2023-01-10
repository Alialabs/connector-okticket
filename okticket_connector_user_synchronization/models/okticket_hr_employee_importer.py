# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class HrEmployeeMapper(Component):
    _name = 'okticket.employee.mapper'
    _inherit = 'okticket.import.mapper'
    _usage = 'mapper'

    _fields_mapping = {'work_email': 'email'}

    def filters_fields_conversion(self, filters):
        processed_filters = {}
        for filter_key in filters.keys():
            processed_filter_key = filter_key
            if filter_key in self._fields_mapping:
                processed_filter_key = self._fields_mapping[filter_key]
            processed_filters[processed_filter_key] = filters[filter_key]
        return processed_filters

    @mapping
    def external_id(self, record):
        return {'external_id': record['id']}

    @mapping
    def work_email(self, record):
        return {'work_email': record['email']}

    @mapping
    def name(self, record):
        return {'name': record['name']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def odoo_id(self, record):
        """ Will bind the category on a existing one with the same name."""
        existing = self.env['hr.employee'].search(
            [('work_email', '=', record['email']),
             ('active', 'in', [True, False])],  # Allows modify an archived employee preventing
                                                # new one creation (duplicaded)
            limit=1,
        )
        if existing:
            return {'odoo_id': existing.id}


class HrEmployeeBatchImporter(Component):
    _name = 'okticket.employee.batch.importer'
    _apply_on = 'okticket.hr.employee'
    _inherit = 'okticket.import.mapper'
    _usage = 'importer'

    def run(self, filters=None, options=None):
        backend_adapter = self.component(usage='backend.adapter')
        okticket_hr_employee_ids = []
        mapper = self.component(usage='mapper')
        filters = mapper.filters_fields_conversion(filters)
        binder = self.component(usage='binder')

        for employee_ext_vals in backend_adapter.search(filters):

            # Map to odoo data
            internal_data = mapper.map_record(employee_ext_vals).values()
            # find if the OkTicket user id already exists in odoo
            binding = binder.to_internal(employee_ext_vals['id'])

            if not binding:
                if internal_data.get('odoo_id'):
                    # User exists in Odoo but its binding is not updated
                    binding = self.model.search([(binder._odoo_field, '=', internal_data['odoo_id']),
                                                 (binder._backend_field, '=', self.backend_record.id)])
                if not binding:
                    # User or user binding do not exist in Odoo
                    binding = self.model.with_context(ignore_okticket_synch=True).create(internal_data)

            binding.write(internal_data)
            binder.bind(employee_ext_vals.get('id'), binding)
            
            okticket_hr_employee_ids.append(binding.id)
            _logger.info('Imported')

        _logger.info(_('Import from Okticket DONE'))
        return okticket_hr_employee_ids


class HrEmployeeRecordImporter(Component):
    _name = 'okticket.employee.record.exporter'
    _apply_on = 'okticket.hr.employee'
    _usage = 'record.importer'

    def run(self, filters=None, options=None):
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        # Read users from OkTicket
        okticket_hr_employee_ids = []
        # Mapper
        mapper = self.component(usage='mapper')
        # Binder
        binder = self.component(usage='binder')

        for employee_ext_vals in backend_adapter.search(filters):
            # Map to odoo data
            internal_data = mapper.map_record(employee_ext_vals).values()
            # find if the OkTicket id already exists in odoo
            binding = binder.to_internal(employee_ext_vals.get('id'))

            if binding:
                # if yes, we update it
                binding.write(internal_data)
            else:
                if internal_data.get('odoo_id'):
                    binding = self.model.create(internal_data)
            if internal_data.get('odoo_id'):
                user = self.env['hr.employee'].browse(internal_data['odoo_id'])
                user.write({'okticket_user_id': employee_ext_vals.get('id')})
            if binding:
                okticket_hr_employee_ids.append(binding.id)
                # finally, we bind both, so the next time we import
                # the record, we'll update the same record instead of
                # creating a new on
                binder.bind(employee_ext_vals.get('id'), binding)
                _logger.info('Imported ')
        _logger.info(_('Import from Okticket DONE'))
        return okticket_hr_employee_ids
