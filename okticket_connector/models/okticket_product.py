from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare


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
    okticket_tax_mapping_ids = fields.One2many(
        'okticket.product.tax.mapping', 'product_tmpl_id',
        string='OkTicket Tax Mapping',
        help="Which Odoo tax each rate OkTicket reports means for this product. "
             "Rows are only needed where the tax the connector would otherwise "
             "resolve is not the right one -- typically a rate that is goods "
             "here, since every expense product is typed as a service."
    )

    def okticket_mapped_tax(self, rate, company_id):
        """The tax this product declares for an OkTicket rate, or an empty set.

        Falls back to the base product, so the decision is declared once on the
        category and inherited by its "-Invoiceable" and "-Rebillable" versions
        instead of being repeated on all three.
        """
        self.ensure_one()
        products = self
        base = self.get_base_product()
        if base and base != self:
            products = self + base
        for product in products:
            row = product.okticket_tax_mapping_ids.filtered(
                lambda m: m.company_id.id == company_id
                and float_compare(m.okticket_rate, rate, precision_digits=2) == 0)
            if row:
                return row[0].tax_id
        return self.env['account.tax']

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

    def _okticket_existing_version(self, name):
        """The product version with this name, whoever created it.

        ``invoice_prod_id`` and ``rebillable_prod_id`` are ``company_dependent``,
        so in another company's context they read empty even when the version
        already exists as a product. Deciding "does it exist?" from that link
        therefore copied the product again for every company, and again after
        every reset that clears ``ir_property`` -- 162 expensable templates for
        61 distinct names on the reference database.

        These products carry no company and every company sees them, so the
        version is looked up by name and merely *linked* for the current company.
        Ordered by id so all companies converge on the same, oldest one.
        """
        self.ensure_one()
        return self.env['product.template'].with_context(active_test=False).search(
            [('name', '=', name), ('can_be_expensed', '=', True)],
            order='id', limit=1)

    def load_rebillable_product_version(self):
        rebillable_products = []
        for product in self:
            rebill_name = f"{product.name}-{_('Rebillable')}"
            rebillable_prod = product.rebillable_prod_id \
                or product._okticket_existing_version(rebill_name)
            if rebillable_prod:
                rebillable_prod.write({
                    'okticket_type_prod_id': product.okticket_type_prod_id,
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
            else:
                rebillable_prod = product.copy(default={
                    'name': rebill_name,
                    'expense_policy': 'cost',
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
            if product.rebillable_prod_id != rebillable_prod:
                # company_dependent: written for the company in context
                product.rebillable_prod_id = rebillable_prod.id
            rebillable_products.append(rebillable_prod)
        return rebillable_products

    def load_invoice_product_version(self):
        _default_invoice_type_id = 1
        invoice_version_products_ids = []
        for product in self.filtered(lambda p: p.okticket_type_prod_id == 0):
            inv_name = f"{product.name}-{_('Invoiceable')}"
            invoice_prod = product.invoice_prod_id \
                or product._okticket_existing_version(inv_name)
            if invoice_prod:
                invoice_prod.write({
                    'okticket_type_prod_id': _default_invoice_type_id,
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
            else:
                invoice_prod = product.copy(default={
                    'name': inv_name,
                    'okticket_type_prod_id': _default_invoice_type_id,
                    'okticket_categ_prod_id': product.okticket_categ_prod_id
                })
            if product.invoice_prod_id != invoice_prod:
                product.invoice_prod_id = invoice_prod.id
            invoice_version_products_ids.append(invoice_prod.id)
        return invoice_version_products_ids
