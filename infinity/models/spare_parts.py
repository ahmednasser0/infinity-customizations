from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools import html2plaintext


def _internal_notes(product):
    """A product's Internal Notes as one plain line.

    The field behind them is HTML on this build, so what comes back carries
    markup. Written straight into a Char it reaches the print as tags rather
    than words, which is what made the column unreadable. The markup is
    stripped here and the line breaks inside it collapsed, because the cell
    it lands in is a single line.
    """
    text = product.description if product else None
    if not text:
        return ''
    return ' '.join(html2plaintext(text).split())


class SpareLine(models.AbstractModel):
    """What the two spare part tables have in common: they report themselves.

    The spare parts are the one part of a Technical Report that stays
    editable after the visit is closed out, so they are the one part that
    can change behind everybody's back. Each table writes what happened into
    its report's chatter - added, removed, or changed from this to that -
    so the change is answerable for afterwards.

    Odoo's own tracking=True is no use here: it follows fields on a record,
    and these are rows under one. So the rows say it themselves.
    """
    _name = 'infinity.spare.line.mixin'
    _description = 'Technical Report Spare Part Line'

    # What the chatter calls this table, and which of its columns are worth
    # a line in the log. Both are answered by the models below.
    _infinity_section = ''
    _infinity_logged = ()

    def _infinity_describe(self):
        """This line as one readable phrase - '2.0 Units x [PN] Name'."""
        self.ensure_one()
        return '%s %s x %s' % (
            self.qty,
            self.uom_id.display_name or '',
            self.product_id.display_name or '',
        )

    @api.model
    def _infinity_log(self, by_report):
        """One chatter entry per report, listing what happened to it.

        The list is built with Markup's own formatting, so a product called
        'Drum & Belt <A4>' reaches the chatter as those words rather than as
        broken markup or a hole in the page.
        """
        for report, items in by_report.items():
            # 'edited' only once the visit has been closed out. Up to then
            # the report is being written for the first time and nothing is
            # being edited - every line added while filling it in would be
            # calling the first draft a correction.
            heading = (
                _('%s edited', self._infinity_section) if report.visit_closed
                else self._infinity_section
            )
            report.message_post(body=Markup('<p><b>%s</b></p><ul>%s</ul>') % (
                heading,
                Markup('').join(Markup('<li>%s</li>') % item for item in items),
            ))

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        by_report = {}
        for line in lines:
            if line.report_id:
                by_report.setdefault(line.report_id, []).append(
                    _('added: %s', line._infinity_describe()))
        self._infinity_log(by_report)
        self._infinity_after_add(lines)
        return lines

    def _infinity_after_add(self, lines):
        """What happens beyond the log when lines arrive. Nothing, here.

        Only the requested parts reach a quotation - see the model below.
        The installed ones are a record of what was fitted, not a thing to
        charge for twice.
        """

    def _infinity_after_change(self, lines):
        """Likewise, when a line is edited."""

    def _infinity_before_remove(self, lines):
        """Likewise, while a line still exists to be matched."""

    def write(self, vals):
        changed = [name for name in self._infinity_logged if name in vals]
        if not changed:
            return super().write(vals)

        # Read before, compare after: the log says what it changed from, not
        # just that it changed, because "qty was edited" answers nothing.
        before = {
            line.id: {name: line[name] for name in changed}
            for line in self
        }
        result = super().write(vals)

        by_report = {}
        for line in self:
            was = before.get(line.id, {})
            parts = []
            for name in changed:
                old, new = was.get(name), line[name]
                if old == new:
                    continue
                field = self._fields[name]
                parts.append('%s: %s -> %s' % (
                    field.string,
                    self._infinity_show(field, old),
                    self._infinity_show(field, new),
                ))
            if parts and line.report_id:
                by_report.setdefault(line.report_id, []).append(
                    _('changed: %s (%s)',
                      line._infinity_describe(), ', '.join(parts)))
        self._infinity_log(by_report)
        self._infinity_after_change(self)
        return result

    @api.model
    def _infinity_show(self, field, value):
        """A field's value as somebody reading the chatter would say it."""
        if field.type == 'many2one':
            return value.display_name or _('nothing') if value else _('nothing')
        if field.type == 'selection':
            return dict(field.selection).get(value) or _('nothing')
        if field.type == 'boolean':
            # 'Quote: nothing -> True' is not a sentence anybody reads
            return _('yes') if value else _('no')
        return value if value not in (False, None) else _('nothing')

    def unlink(self):
        # Said before the rows go: afterwards there is nothing left to read.
        by_report = {}
        for line in self:
            if line.report_id:
                by_report.setdefault(line.report_id, []).append(
                    _('removed: %s', line._infinity_describe()))
        self._infinity_log(by_report)
        self._infinity_before_remove(self)
        return super().unlink()


class SpareRequested(models.Model):
    _name = 'infinity.technical.report.spare.requested'
    _inherit = ['infinity.spare.line.mixin']
    _description = 'Technical Report Spare Part Requested'
    _infinity_section = 'Spare Parts Requested'
    # to_quotation is logged with the rest: which of the two ways a part
    # goes out is the sort of change somebody has to answer for afterwards.
    _infinity_logged = ('product_id', 'qty', 'to_quotation')

    # The quotation is meant to be what this report is asking for, so it
    # keeps up: a part added goes onto it, a part edited is edited on it, a
    # part withdrawn comes off it. All three stop at the same line - once
    # the quotation has been confirmed it is an order somebody agreed to,
    # and a report does not reach into that. Parts asked for after that go
    # on a fresh quotation, through the button.
    #
    # All of this happens when the report is saved, because until then the
    # lines do not exist for anything to be told about.
    def _infinity_by_report(self, lines):
        by_report = {}
        for line in lines:
            if line.report_id:
                by_report.setdefault(line.report_id, self.browse())
                by_report[line.report_id] |= line
        return by_report

    def _infinity_after_add(self, lines):
        for report, added in self._infinity_by_report(lines).items():
            wanted = added.filtered('to_quotation')
            # The consumed ones join the transfer still waiting to go out,
            # where there is one. Where there is not, the button raises it.
            report._infinity_deliver_lines(added - wanted)
            # And the charged ones join the open quotation - or, where the
            # last one has been confirmed, are quoted by themselves rather
            # than squeezed into an agreed order. Nothing quoted yet, and
            # the button makes the first one.
            report._infinity_quote_pending(wanted)

    def _infinity_after_change(self, lines):
        """Carry the change to the quotation and to the transfer.

        A part is on one or the other, and Quote says which, so a change
        to a line is told to both: the side the part is on takes the new
        product and quantity, and the side it is not on lets go of it.
        That covers the tick moving as well - unticking Quote takes the
        part off the quotation and puts it on the transfer, and ticking it
        does the reverse.
        """
        for report, changed in self._infinity_by_report(lines).items():
            quoted = changed.filtered('to_quotation')
            consumed = changed - quoted
            report._infinity_requote_lines(quoted)
            report._infinity_undeliver_lines(quoted)
            report._infinity_unquote_lines(consumed)
            report._infinity_redeliver_lines(consumed)

    def _infinity_before_remove(self, lines):
        for report, going in self._infinity_by_report(lines).items():
            report._infinity_unquote_lines(going)
            report._infinity_undeliver_lines(going)
    _order = 'report_id, id'

    report_id = fields.Many2one(
        'infinity.technical.report', string='Technical Report',
        required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='P/N', required=True)

    # The product's Internal Notes, shown beside the part number.
    description = fields.Char(string='Description', compute='_compute_description')

    @api.depends('product_id', 'product_id.description')
    def _compute_description(self):
        for line in self:
            line.description = _internal_notes(line.product_id)

    uom_id = fields.Many2one(
        related='product_id.uom_id', string='Unit', readonly=True)
    qty = fields.Float(string='Qty')

    # Which of the two ways this part goes out. Ticked, it is charged for
    # and goes on the quotation. Unticked, it is material consumed under
    # the contract: nobody is billed and it leaves on a transfer instead,
    # through Deliver Consumed Materials.
    #
    # Ticked by default, because that is what every line did before this
    # existed and a part nobody has said anything about is a part being
    # asked for.
    to_quotation = fields.Boolean(
        string='Quote', default=True,
        help='Ticked: this part goes on the quotation. Unticked: it is '
             'consumed under the contract and goes out on a transfer, '
             'through Deliver Consumed Materials.')

    @api.depends('product_id')
    def _compute_display_name(self):
        for line in self:
            line.display_name = line.product_id.display_name or ''


class SpareInstalled(models.Model):
    _name = 'infinity.technical.report.spare.installed'
    _inherit = ['infinity.spare.line.mixin']
    _description = 'Technical Report Spare Part Installed'
    # part_source is logged here and not on the requested lines, because
    # only these have it: whose stock the part came out of is a question
    # that arises once it has actually gone in.
    _infinity_section = 'Spare Parts Installed'
    _infinity_logged = ('product_id', 'qty', 'part_source')
    _order = 'report_id, id'

    report_id = fields.Many2one(
        'infinity.technical.report', string='Technical Report',
        required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='P/N', required=True)

    # The product's Internal Notes, as on the requested lines above.
    description = fields.Char(string='Description', compute='_compute_description')

    @api.depends('product_id', 'product_id.description')
    def _compute_description(self):
        for line in self:
            line.description = _internal_notes(line.product_id)

    uom_id = fields.Many2one(
        related='product_id.uom_id', string='Unit', readonly=True)
    qty = fields.Float(string='Qty')

    # Who the part came out of - the fitter's own stock, or the customer's.
    part_source = fields.Selection([
        ('infinity', 'Infinity'),
        ('customer', 'Customer'),
    ], string='Source', default='infinity')

    @api.depends('product_id')
    def _compute_display_name(self):
        for line in self:
            line.display_name = line.product_id.display_name or ''
