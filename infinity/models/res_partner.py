from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """Two names a contact goes by, and a document it has to come with.

    The prefix on the two fields is there because res.partner is a model
    everything extends - localisations, accounting, the lot. A field called
    plainly abbreviation would be a coin toss between adjusting somebody
    else's and inventing a second one that shadows it.
    """
    _inherit = 'res.partner'

    infinity_arabic_name = fields.Char(string='Arabic Name')
    infinity_abbreviation = fields.Char(string='Abbreviation')

    # The fields somebody edits on a contact's own form. A save that touches
    # one of these is a person working on the contact, and is asked for the
    # document. Writes that touch none of them are Odoo's own bookkeeping -
    # customer_rank going up when the contact is put on an order,
    # message_main_attachment_id when a file is filed - and asking those for
    # a document would stop sales orders being made, which is not what was
    # wanted.
    _INFINITY_CONTACT_FIELDS = frozenset((
        'name', 'infinity_arabic_name', 'infinity_abbreviation',
        'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
        'vat', 'category_id', 'phone', 'email', 'website', 'function',
        'company_type', 'is_company', 'comment',
    ))

    def _infinity_has_attachment(self):
        """Whether anything has been filed against this contact."""
        self.ensure_one()
        return bool(self.env['ir.attachment'].sudo().search_count([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', self.id),
        ]))

    def write(self, vals):
        """A customer record has to carry a document.

        Asked when the contact is saved, and not when it is first created -
        which is not a softening of what was asked for, it is the only
        moment the question can be asked at all. A file dropped on the
        chatter is filed a moment *after* the contact is written, because
        until the contact exists there is nothing for the file to point at.
        A check at creation would find nothing every single time, and no
        contact could ever be made.

        So: make the contact, attach the document, and every save from then
        on checks it is still there. Only top-level contacts are asked - a
        person listed under a company is reached through the company's file.
        """
        result = super().write(vals)

        if self.env.context.get('infinity_skip_attachment_check'):
            return result
        if not self._INFINITY_CONTACT_FIELDS.intersection(vals):
            return result

        for partner in self:
            if partner.parent_id or not partner.active:
                continue
            if not partner._infinity_has_attachment():
                raise ValidationError(_(
                    'Attach the customer document to %(name)s before saving '
                    'it. Use the paperclip at the bottom of the form, then '
                    'save again.',
                    name=partner.display_name or _('this contact'),
                ))
        return result
