from odoo import fields, models


class ResPartner(models.Model):
    """What a contact carries beyond the name Odoo already holds.

    The prefix is there because res.partner is a model everything extends -
    localisations, accounting, the lot. A field called plainly abbreviation
    would be a coin toss between adjusting somebody else's and inventing a
    second one that shadows it.
    """
    _inherit = 'res.partner'

    # Whether this partner is one of ours to sell to, and so one we have
    # to know properly. Every demand on this form hangs off it.
    #
    # It is what makes those demands safe to make at all. Asked of every
    # partner, they would be asked of the ones Odoo creates by itself - a
    # vendor, a delivery address, the partner behind each new user, a
    # portal signup, an import, and every partner built in another
    # module's tests. Off by default, they are asked only of the records
    # somebody has actually marked as a customer.
    infinity_is_customer = fields.Boolean(string='Is Customer')

    infinity_arabic_name = fields.Char(string='Arabic Name')
    infinity_abbreviation = fields.Char(string='Abbreviation')

    # The customer's document, on the form rather than in the chatter. A
    # file dropped on the chatter is filed a moment after the contact is
    # written, so nothing can check for it while the contact is being made;
    # a field on the form is answered before the save, which is where the
    # question belongs.
    infinity_attachment = fields.Binary(string='Attachment', attachment=True)
    infinity_attachment_name = fields.Char(string='Attachment Name')
