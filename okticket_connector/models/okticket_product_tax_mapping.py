# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OkticketProductTaxMapping(models.Model):
    """Which Odoo tax an OkTicket rate means, decided per product.

    OkTicket reports a bare percentage, and a Spanish chart carries a dozen
    purchase taxes for each one -- for 10% alone: goods, investment goods and
    services, plus the intra-community, import and reverse-charge variants of
    each. The connector can narrow that down structurally, but only as far as
    "the domestic tax of the product's scope", and it types *every* expense
    product as a service, so nothing else in the model can express that a given
    10% receipt is goods. That decision belongs here.

    Rows carry their company as a visible column rather than the field being
    ``company_dependent``: ``account.tax`` is company-specific, and this keeps
    the mapping auditable in the form instead of hidden in ``ir_property``.
    """

    _name = 'okticket.product.tax.mapping'
    _description = 'OkTicket Rate to Odoo Tax Mapping'
    _order = 'product_tmpl_id, company_id, okticket_rate'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string='Product',
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        required=True, index=True, default=lambda self: self.env.company)
    okticket_rate = fields.Float(
        string='OkTicket Rate (%)', required=True, digits=(5, 2),
        help="The percentage OkTicket reports in the receipt's tax breakdown "
             "(the 'p' of each entry). 0 is a valid rate and is not the same "
             "as having no row.")
    tax_id = fields.Many2one(
        comodel_name='account.tax', string='Odoo Tax', required=True,
        domain="[('type_tax_use', '=', 'purchase'),"
               " ('company_id', '=', company_id)]")

    _sql_constraints = [
        ('okticket_product_rate_uniq',
         'unique(product_tmpl_id, company_id, okticket_rate)',
         'A product can map an OkTicket rate to only one tax per company.'),
    ]

    @api.constrains('tax_id', 'company_id')
    def _check_tax_company(self):
        for row in self:
            if row.tax_id.company_id and row.tax_id.company_id != row.company_id:
                raise ValidationError(_(
                    'The tax "%(tax)s" belongs to company "%(tax_company)s" but '
                    'the mapping row is for "%(company)s".',
                    tax=row.tax_id.display_name,
                    tax_company=row.tax_id.company_id.display_name,
                    company=row.company_id.display_name))
