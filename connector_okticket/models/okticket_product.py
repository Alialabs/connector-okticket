# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    okticket_categ_prod_id = fields.Integer(string="OkTicket Category_id", default=-1.0)
    okticket_type_prod_id = fields.Integer(string="OkTicket Type_id", default=-1.0)
    # Product.template's "rebillable" version
    rebillable_prod_id = fields.Many2one('product.template', company_dependent=True,
                                         string="Rebillable product version",
                                         help="Rebillable version of the product")
    no_rebillable_prod_ids = fields.One2many('product.template', 'rebillable_prod_id',
                                             string='No rebillable product version')
    rebillable_product_version = fields.Boolean("Is rebillable product version", store=True,
                                                help="True if the product has other version no rebillable")

    # Product.template's "invoiceable" version
    invoice_prod_id = fields.Many2one('product.template', company_dependent=True,
                                      string="Invoice product version",
                                      help="Version of the product to use in invoices")
    base_version_prod_ids = fields.One2many('product.template', 'invoice_prod_id',
                                            string='Base product version')

    def copy(self, default=None):
        default = default or {}
        if 'rebillable_prod_id' not in default:
            default.update({
                'rebillable_prod_id': False,
            })
        if 'invoice_prod_id' not in default:
            default.update({
                'invoice_prod_id': False,
            })
        return super().copy(default)

    @api.depends('rebillable_prod_id')
    def _compute_is_rebillable_product(self):
        if self.rebillable_prod_id:
            # If product has a rebillable version, then it is not rebillable
            # (because it exists another product to do this operation)
            self.rebillable_product_version = False
        else:
            # If product has not a rebillable version, then it is rebillable
            # (because it doesn't exists another product to do this operation)
            self.rebillable_product_version = True

    def load_rebillable_product_version(self):
        """
        Updates or creates product.template in a "rebillable" version from the one indicated
        """
        rebillable_products = []
        for no_rebill_prod in self:
            rebillable_prod = no_rebill_prod.rebillable_prod_id or False
            # Updates each product.template "rebillable" if exists
            if rebillable_prod:
                rebillable_prod.write({
                    'okticket_type_prod_id': rebillable_prod.okticket_type_prod_id,
                    'okticket_categ_prod_id': rebillable_prod.okticket_categ_prod_id,
                })
            else:  # If not, it creates new product.template "rebillable" version
                rebill_sufix = _('Rebillable')
                rebill_name = no_rebill_prod.name + '-' + rebill_sufix
                rebillable_prod = no_rebill_prod.copy(default={
                    'name': rebill_name,
                    'expense_policy': 'cost',  # "Re-Invoice Policy"
                })
                no_rebill_prod.write({'rebillable_prod_id': rebillable_prod.id})
            rebillable_products.append(rebillable_prod)
        return rebillable_products

    def load_invoice_product_version(self):
        """
        Updates or creates product.template in a "invoiceable" version from the one indicated
         (okticket_type_prod_id = 1)
        """
        _default_invoice_type_id = 1  # Default invoice type id
        invoice_version_products_ids = []
        for base_prod in self.filtered(lambda p: p.okticket_type_prod_id == 0):
            invoice_version_prod = base_prod.invoice_prod_id or False
            # Updates each product.template "invoiceable" if exists
            if invoice_version_prod:
                invoice_version_prod.write({
                    'okticket_type_prod_id': _default_invoice_type_id,
                    'okticket_categ_prod_id': invoice_version_prod.okticket_categ_prod_id,
                })
            else:  # If not, it creates new product.template "invoiceable" version
                invoiceable_sufix = _('Invoiceable')
                inv_name = base_prod.name + '-' + invoiceable_sufix
                invoice_version_prod = base_prod.copy(default={
                    'name': inv_name,
                    'okticket_type_prod_id': _default_invoice_type_id,
                })
                base_prod.write({'invoice_prod_id': invoice_version_prod.id})
            invoice_version_products_ids.append(invoice_version_prod.id)
        return invoice_version_products_ids
