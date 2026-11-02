from odoo import fields, models


class ResPartner(models.Model):
    """Two names a contact goes by, beside the one Odoo already holds.

    The prefix is there because res.partner is a model everything extends -
    localisations, accounting, the lot. A field called plainly abbreviation
    would be a coin toss between adjusting somebody else's and inventing a
    second one that shadows it.
    """
    _inherit = 'res.partner'

    infinity_arabic_name = fields.Char(string='Arabic Name')
    infinity_abbreviation = fields.Char(string='Abbreviation')
