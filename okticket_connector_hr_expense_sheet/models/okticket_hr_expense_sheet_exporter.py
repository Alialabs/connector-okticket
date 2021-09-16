# -*- coding: utf-8 -*-
#
#    Created on 31/07/19
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
from odoo.addons.connector.components.mapper import mapping
import logging

from datetime import datetime

_logger = logging.getLogger(__name__)

class HrExpenseSheetMapper(Component):
    _name = 'okticket.expense.sheet.mapper'
    _inherit = 'okticket.import.mapper'
    _apply_on = 'okticket.hr.expense.sheet'
    _usage = 'mapper'

    @mapping
    def external_id(self, record):
        return {'external_id': record['_id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    # @mapping
    # def odoo_id(self, record):
    #     """ Will bind the category on a existing one with the same name."""
    #     existing = self.env['hr.employee'].search(
    #         [('work_email', '=', record['email'])],
    #         limit=1,
    #     )
    #     if existing:
    #         return {'odoo_id': existing.id}

class HrExpenseExporter(Component):
    _name = 'okticket.hr.expense.sheet.exporter'
    _inherit = 'okticket.export.mapper'
    _apply_on = 'okticket.hr.expense.sheet'
    _usage = 'record.exporter'

    def generate_new_expense_sheet(self, expense_sheet, backend_adapter):
        '''
        Genera una nueva hoja de gasto modificando el nombre para eliminar conflictos con otra hoja ya existente
        en Okticket pero que esta en un estado distinto de 'draft', tiene vinculado un método de pago o un empleado
        distinto al del gasto que se quiere incluir.
        '''
        # Si no crea correctamente la hoja es porque ya existe una con el mismo nombre
        index = 0
        date_now = datetime.now()
        date_str = str(date_now)[:-7]
        new_name_to_test = expense_sheet.name + '-' + date_str
        new_name_to_test = new_name_to_test.replace(" ", "_")
        found_exp_sheets = True
        max_tries = 20 # Intentara generar nombres hasta 20 veces
        while found_exp_sheets:
            found_exp_sheets = backend_adapter.search({'name': new_name_to_test})
            if found_exp_sheets:
                new_name_to_test = new_name_to_test + '-' + str(index)
                index += 1
            max_tries -= 1
            if max_tries == 0 :
                raise Exception("(generate_new_expense_sheet): No se encuentra un nombre valido para la hoja de gastos "
                                " que se intenta crear en okticket: %s", expense_sheet.name)
        expense_sheet = self.env['hr.expense.sheet'].browse(expense_sheet.id)
        expense_sheet.write({'name': new_name_to_test})
        return backend_adapter.create(expense_sheet)

    def run(self, *args):
        """
        Crea nueva hoja de gastos y actualiza los gastos que contiene
        """
        backend_adapter = self.component(usage='backend.adapter')
        binder = self.component(usage='binder')
        expense_sheet = args and args[0] or False
        if expense_sheet:
            binding = expense_sheet.okticket_bind_ids and \
            expense_sheet.okticket_bind_ids[0] or False
            if not binding:
                # Crear en OkTicket hoja de gasto y la vincula con la hr.expense.sheet de Odoo
                creation_result = backend_adapter.create(expense_sheet)


                # TODO : solucion temporal. Se crea nueva hoja de gastos para evitar conflicto con otra existente
                # ya procesada, con otro metodo de pago u otro empleado distinto del gasto que se va a incluir
                if not creation_result:
                    creation_result = self.generate_new_expense_sheet(expense_sheet, backend_adapter)


                mapper = self.component(usage='mapper')
                external_data = creation_result['data']
                internal_data = mapper.map_record(external_data).values()
                internal_data.update({'odoo_id': expense_sheet.id,})
                binding = self.model.create(internal_data)
                binder.bind(internal_data['external_id'], binding)
                _logger.info('Created and synchronized expense sheet')
            # else:
            # Existe el binding, se actualiza la info de la hoja de gastos de OkTicket
            # Se recuperan los gastos de la hoja de gastos en Okticket son los mismos que en Odoo
            expenses_sheet = backend_adapter.get_expenses_sheet(binding.external_id).get('data', [])
            expenses_external_ids_in_oktk = [expense['_id'] for expense in expenses_sheet if '_id' in expense]
            expenses_to_add = [] # Gastos Odoo para añadir a la hoja de gastos de Okticket
            for expense in expense_sheet.expense_line_ids:
                if expense.okticket_bind_ids:
                    if not expense.okticket_bind_ids[0].external_id in expenses_external_ids_in_oktk:
                        expenses_to_add.append(expense)
                    else:
                        expenses_external_ids_in_oktk.remove(expense.okticket_bind_ids[0].external_id)
            if expenses_external_ids_in_oktk:
                # Se deben eliminar los gastos que están asociados a la hoja en Okticket pero NO existen en Odoo
                # No debería darse este caso, implicaría gestión de hojas de gastos desde Okticket
                backend_adapter.unlink_expenses_sheet(expenses_external_ids_in_oktk) # TODO
            if expenses_to_add:
                # Añadir a la hoja de gastos de Okticket los gastos que están en la hoja de gastos de Odoo
                backend_adapter.link_expenses_sheet(binding.external_id, expenses_to_add)  # TODO

                # TODO: ACTUALIZAR HOJA DE GASTO EN OKTICKET CON LA INFO DE LOS NUEVOS GASTOS


        # self.binding = binding
        # self.external_id = binder.to_external(self.binding)
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: