from odoo import fields, models


class ResPartner(models.Model):
    """Two names a contact goes by, beside the one Odoo already holds.

    The prefix is there because res.partner is a model everything extends -
    localisations, accounting, the lot. A field called plainly abbreviation
    would be a coin toss between adjusting somebody else's and inventing a
    second one that shadows it.

    0.76 also demanded an attachment on every contact, enforced from
    write(). It is gone, on purpose and not just because it was in the way.
    res.partner is written to by half of Odoo - a sales order raising
    customer_rank, an invoice, a user signing up, a module's own update -
    and a rule that can refuse any of those is not a validation, it is a
    trapdoor under everything. The ten fields the contacts form asks for
    are asked on the form, where only a person filling it in is answering.
    """
    _inherit = 'res.partner'

    infinity_arabic_name = fields.Char(string='Arabic Name')
    infinity_abbreviation = fields.Char(string='Abbreviation')
