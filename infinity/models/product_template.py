from odoo import fields, models


class ProductTemplate(models.Model):
    """Where a machine's model and manufacturer are answered.

    They used to be typed on each Technical Report, which meant the same
    machine could be a KM-C3320i on one visit and a KMC3320i on the next,
    and neither was wrong because neither was checked. Answered on the
    product, there is one answer, and every report reads it.

    The names carry the infinity_ prefix because product.template is a model
    half of Odoo extends: a field called plainly manufacturer would be a
    coin toss between adjusting somebody else's and inventing a second one
    that shadows it.
    """
    _inherit = 'product.template'

    infinity_machine_model = fields.Char(string='Machine Model')
    infinity_manufacturer = fields.Char(string='Manufacturer')


class ProductProduct(models.Model):
    """The two fields as a variant reads them.

    Technical Reports find the machine through its serial, and a serial
    belongs to a product.product, not to the template above it - so the
    variant has to be able to answer for itself.
    """
    _inherit = 'product.product'

    infinity_machine_model = fields.Char(
        related='product_tmpl_id.infinity_machine_model', readonly=True)
    infinity_manufacturer = fields.Char(
        related='product_tmpl_id.infinity_manufacturer', readonly=True)
