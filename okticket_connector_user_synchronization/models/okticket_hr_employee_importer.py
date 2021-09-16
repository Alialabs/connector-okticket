# -*- coding: utf-8 -*-
#
#    Created on 2/05/19
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


from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
import logging

_logger = logging.getLogger(__name__)

class HrEmployeeMapper(Component):
    _name = 'okticket.employee.mapper'
    _inherit = 'okticket.import.mapper'
    _usage = 'mapper'

    _fields_mapping = {'work_email': 'email',} # Campos Odoo-Okticket

    def filters_fields_conversion(self, filters):
        # Conversión de campos Odoo-Okticket para filtrado
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
            [('work_email', '=', record['email'])],
            limit=1,
        )
        if existing:
            return {'odoo_id': existing.id}


class HrEmployeeBatchImporter(Component):
    _name = 'okticket.employee.batch.importer'
    _apply_on = 'okticket.hr.employee'
    _usage = 'importer'

    def run(self, filters=None, options=None):
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
            # if binding:
            #     # if yes, we update it
            #     binding.write(internal_data)
            # else:
            #     if internal_data.get('odoo_id'):
            #         binding = self.model.create(internal_data)
            # if internal_data.get('odoo_id'):
            #     user = self.env['hr.employee'].browse(internal_data['odoo_id'])
            #     user.write({'okticket_user_id': employee_ext_vals['id']})
            # if binding:
            #     okticket_hr_employee_ids.append(binding.id)
            #     # finally, we bind both, so the next time we import
            #     # the record, we'll update the same record instead of
            #     # creating a new on
            #     binder.bind(employee_ext_vals['id'], binding)
            #     _logger.info('Imported ')

            user_to_bind_vals = {
                'okticket_user_id': employee_ext_vals.get('id'),
                'work_email': employee_ext_vals.get('email'),
                'name': employee_ext_vals.get('name'),
            }
            odoo_user = False  # Siempre adquiere un valor a lo largo de los if-else...
            if binding:  # EXISTE usuario y están VINCULADO = ACTUALIZAR
                binding.write(internal_data)
                odoo_user = self.env['hr.employee'].browse(internal_data['odoo_id'])
                # odoo_user.write(product_to_bind_vals)
            else:  # NO está VINCULADO
                if not internal_data.get('odoo_id'):  # NO EXISTE
                    # Creación del hr.employee con la información de OkTicket
                    odoo_user = self.env['hr.employee'].\
                        with_context(ignore_okticket_synch=True).create(user_to_bind_vals)
                else:  # EXISTE el producto en Odoo pero NO está VINCULADO
                    odoo_user = self.env['hr.employee'].browse(internal_data['odoo_id'])
                    odoo_user.write(user_to_bind_vals)
                # Vinculación entre el empleado creado o ya existente en Odoo y el usuario de Okticket
                internal_data['odoo_id'] = odoo_user.id
                binding = self.model.create(internal_data)
            if binding:
                okticket_hr_employee_ids.append(binding.id)
                if 'id' in employee_ext_vals:
                    external_id = str(employee_ext_vals['id'])
                    binder.bind(external_id, binding)
                    _logger.info('Imported')
                    
        _logger.info('Import from Okticket DONE !!!')
        return okticket_hr_employee_ids

class HrEmployeeRecordImporter(Component): # ---------------------------- POR HORA NO ESTA SIENDO USADO!!!!!!
    _name = 'okticket.employee.record.exporter'
    _apply_on = 'okticket.hr.employee'
    _usage = 'record.importer' # Será llamada por una record de hr.employee

    def run(self, filters=None, options=None):
        # TODO: ejecuta el run del import_batch añadiendo los filtros que se propagan al search()
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
        _logger.info('Import from Okticket DONE !!!')
        return okticket_hr_employee_ids


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: