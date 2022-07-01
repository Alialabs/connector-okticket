# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging

from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountAnalyticAccountCostCenter(models.TransientModel):
    """
    This wizard will confirm cost_center creation from analytic accounts
    """

    _name = 'analytic.cost.center.wizard'
    _description = "Confirm cost center creation from analytic account"

    confirm_duplicate = fields.Boolean('Confirm Duplicate', default=False)
    duplicate_confirmation_needed = fields.Boolean('Duplicate Confirmation Needed', default=False)

    def cost_center_from_analytic_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        warning_analytic = []
        result = {'type': 'ir.actions.act_window_close'}
        for record in self.env['account.analytic.account'].browse(active_ids):
            if not record.okticket_bind_ids:

                if self.duplicate_confirmation_needed and self.confirm_duplicate:
                    # Se necesita confirmación de creación de CC duplicado y se tiene confirmación
                    record._okticket_create()  # No comprueba duplicados
                elif self.duplicate_confirmation_needed and not self.confirm_duplicate:
                    # Se necesita confirmación de creación de CC duplicado PERO no se tiene confirmación
                    raise ValidationError('Check the box if you want to create a duplicated cost center '
                                          '\nand continue or cancel operation.')
                else:
                    # Comprueba si existe un CC con el mismo nombre y pregunta por confirmación
                    result = record._okticket_create_duplicates_control()

                    if not result:
                        if len(active_ids) > 1:
                            # Si existe conflicto de posible duplicado,
                            # no se permite procesar todas las cuentas analíticas simultáneamente
                            raise ValidationError('There is a conflict in one or more analytic accounts selected.'
                                                  '\nPlease, process them one at a time.')
                        else:
                            self.duplicate_confirmation_needed = True
                            return {
                                'name': 'Confirm Cost Center Creation from Analytic',
                                'view_mode': 'form',
                                'res_model': 'analytic.cost.center.wizard',
                                'views': [(self.env.ref('okticket_connector_cost_center.cost_center_creation_from_analytic_view').id, 'form')],
                                'type': 'ir.actions.act_window',
                                'res_id': self.id,
                                'target': 'new',
                                'context': self.env.context,
                            }
            else:
                warning_analytic.append(record.name)
        if warning_analytic:
            warning_msg = 'These analytic accounts have already a related cost center: %s' % warning_analytic
            _logger.warning(warning_msg)
            raise ValidationError(warning_msg)
        return result
