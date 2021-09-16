# -*- coding: utf-8 -*-
#
#    Created on 6/05/19
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


from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    okticket_categ_prod_id = fields.Integer(string="OkTicket Category_id", default=-1.0)
    okticket_type_prod_id = fields.Integer(string="OkTicket Type_id", default=-1.0)
    # Producto versión "refacturable" del product.template
    reinvoiceable_prod_id = fields.Many2one('product.template', company_dependent=True,
                                    string="Reinvoiceable product version",
                                    help="Reinvoiceable version of the product")
    no_reinvoiceable_prod_ids = fields.One2many('product.template', 'reinvoiceable_prod_id',
                                    string='No reinvoiceable product version')
    reinvoiceable_product_version = fields.Boolean("Is reinvoiceable product version", store=True,
                                    # compute='_compute_is_reinvoiceable_product',
                                    help="True if the product has other version no reinvoiceable")

    @api.depends('reinvoiceable_prod_id')
    def _compute_is_reinvoiceable_product(self):
        if self.reinvoiceable_prod_id: # Si el producto tiene versión refacturable, entonces es NO refacturable
            self.reinvoiceable_product_version =  False
        else: # Si el producto NO tiene versión refacturable, entonces ES refacturable
            self.reinvoiceable_product_version = True

    @api.multi
    def load_reinvoiceable_product_version(self):
        '''
        Actualización/creación de un product.template en versión "reinvoiceable" a partir del indicado
        '''
        reinvoiceable_products = []
        for no_reinv_prod in self:
            reinvoiceable_prod = no_reinv_prod.reinvoiceable_prod_id or False
            # Se actualiza la versión "refacturable" de cada product.template si ya tiene una
            if reinvoiceable_prod:
                reinvoiceable_prod.write({
                    'okticket_type_prod_id': reinvoiceable_prod.okticket_type_prod_id,
                    'okticket_categ_prod_id': reinvoiceable_prod.okticket_categ_prod_id,
                })
            else:# Si no, se crea un nuevo product.template versión "refacturable"
                reinv_name = no_reinv_prod.name + '-REFACTURABLE' # todo: otra forma de nombrar la verión "refacturable" ??
                reinvoiceable_prod = no_reinv_prod.copy(default={
                    'name': reinv_name,
                    'expense_policy': 'cost', # "Re-Invoice Policy" = 'A costo'
                })
                no_reinv_prod.write({'reinvoiceable_prod_id': reinvoiceable_prod.id})
            reinvoiceable_products.append(reinvoiceable_prod)
        return reinvoiceable_products


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: