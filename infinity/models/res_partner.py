from odoo import fields, models


class ResPartner(models.Model):
    """What a contact carries beyond the name Odoo already holds.

    The prefix is there because res.partner is a model everything extends -
    localisations, accounting, the lot. A field called plainly abbreviation
    would be a coin toss between adjusting somebody else's and inventing a
    second one that shadows it.
    """
    _inherit = 'res.partner'

    infinity_arabic_name = fields.Char(string='Arabic Name')
    infinity_abbreviation = fields.Char(string='Abbreviation')

    # The customer's document, on the form rather than in the chatter. A
    # file dropped on the chatter is filed a moment after the contact is
    # written, so nothing can check for it while the contact is being made;
    # a field on the form is answered before the save, which is where the
    # question belongs.
    infinity_attachment = fields.Binary(string='Attachment', attachment=True)
    infinity_attachment_name = fields.Char(string='Attachment Name')
