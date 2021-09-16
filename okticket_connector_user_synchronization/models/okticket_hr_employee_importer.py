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
        for filter_key in filters.keys():
            if filter_key in self._fields_mapping:
                filters[self._fields_mapping[filter_key]] = filters.pop(filter_key)
        return filters

    @mapping
    def external_id(self, record):
        return {'external_id': record['id']}

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
    _usage = 'importer'

    def run(self, filters=None, options=None):
        employee_obj = self.env['hr.employee']
        # Adapter
        backend_adapter = self.component(usage='backend.adapter')
        # Read users from OkTicket
        okticket_hr_employee_ids = []
        # Mapper
        mapper = self.component(usage='mapper')
        filters = mapper.filters_fields_conversion(filters)
        # Binder
        binder = self.component(usage='binder')
        for employee_ext_vals in backend_adapter.search(filters):
            # Map to odoo data
            internal_data = mapper.map_record(employee_ext_vals).values()
            # find if the OkTicket id already exists in odoo
            binding = binder.to_internal(employee_ext_vals['id'])

            user_to_bind_vals = {
                'okticket_user_id': employee_ext_vals.get('id'),
                'work_email': employee_ext_vals.get('email'),
                'name': employee_ext_vals.get('name'),
            }
            odoo_user = False
            if binding:  # User exists and is bound (UPDATE)
                binding.write(internal_data)
                odoo_user = employee_obj.browse(internal_data['odoo_id'])
            else:  # User doesn't bound
                if not internal_data.get('odoo_id'):
                    # User doesn't exist
                    odoo_user = employee_obj. \
                        with_context(ignore_okticket_synch=True).create(user_to_bind_vals)
                else:
                    # User exists but is not bound
                    odoo_user = employee_obj.browse(internal_data['odoo_id'])
                    odoo_user.write(user_to_bind_vals)
                # Binding between Odoo employee and Okticket user
                internal_data['odoo_id'] = odoo_user.id
                binding = self.model.create(internal_data)
            if binding:
                okticket_hr_employee_ids.append(binding.id)
                if 'id' in employee_ext_vals:
                    external_id = str(employee_ext_vals['id'])
                    binder.bind(external_id, binding)
                    _logger.info(_('Imported'))

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
