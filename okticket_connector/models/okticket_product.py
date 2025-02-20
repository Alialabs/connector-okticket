from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    okticket_categ_prod_id = fields.Integer(string="OkTicket Category ID", default=-1)
    okticket_type_prod_id = fields.Integer(string="OkTicket Type ID", default=-1)
    rebillable_prod_id = fields.Many2one(
        'product.template', company_dependent=True,
        string="Rebillable Product Version",
        help="Rebillable version of the product"
    )
    no_rebillable_prod_ids = fields.One2many(
        'product.template', 'rebillable_prod_id',
        string='Non-Rebillable Product Versions'
    )
    rebillable_product_version = fields.Boolean(
        "Is Rebillable Product Version", store=True,
        help="True if the product has other versions that are non-rebillable"
    )
    invoice_prod_id = fields.Many2one(
        'product.template', company_dependent=True,
        string="Invoice Product Version",
        help="Version of the product to use in invoices"
    )
    base_version_prod_ids = fields.One2many(
        'product.template', 'invoice_prod_id',
        string='Base Product Versions'
    )

    def get_base_product(self):
        self.ensure_one()
        if self.base_version_prod_ids:
            return self.base_version_prod_ids[0]
        elif self.no_rebillable_prod_ids:
            return self.no_rebillable_prod_ids[0]
        return self

    def copy(self, default=None):
        default = default or {}
        default.setdefault('rebillable_prod_id', False)
        default.setdefault('invoice_prod_id', False)
        return super().copy(default)

    @api.depends('rebillable_prod_id')
    def _compute_is_rebillable_product(self):
        for product in self:
            product.rebillable_product_version = not bool(product.rebillable_prod_id)

    def load_rebillable_product_version(self):
        rebillable_products = []
        for product in self:
            rebillable_prod = product.rebillable_prod_id
            if rebillable_prod:
                rebillable_prod.write({
                    'okticket_type_prod_id': product.okticket_type_prod_id,
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
            else:
                rebill_name = f"{product.name}-{_('Rebillable')}"
                rebillable_prod = product.copy(default={
                    'name': rebill_name,
                    'expense_policy': 'cost',
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
                product.rebillable_prod_id = rebillable_prod.id
            rebillable_products.append(rebillable_prod)
        return rebillable_products

    def load_invoice_product_version(self):
        _default_invoice_type_id = 1
        invoice_version_products_ids = []
        for product in self.filtered(lambda p: p.okticket_type_prod_id == 0):
            invoice_prod = product.invoice_prod_id
            if invoice_prod:
                invoice_prod.write({
                    'okticket_type_prod_id': _default_invoice_type_id,
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
            else:
                inv_name = f"{product.name}-{_('Invoiceable')}"
                invoice_prod = product.copy(default={
                    'name': inv_name,
                    'okticket_type_prod_id': _default_invoice_type_id,
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
                product.invoice_prod_id = invoice_prod.id
            invoice_version_products_ids.append(invoice_prod.id)
        return invoice_version_products_ids
