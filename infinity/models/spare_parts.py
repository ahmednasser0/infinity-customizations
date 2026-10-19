from odoo import api, fields, models
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


class SpareRequested(models.Model):
    _name = 'infinity.technical.report.spare.requested'
    _description = 'Technical Report Spare Part Requested'
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

    @api.depends('product_id')
    def _compute_display_name(self):
        for line in self:
            line.display_name = line.product_id.display_name or ''


class SpareInstalled(models.Model):
    _name = 'infinity.technical.report.spare.installed'
    _description = 'Technical Report Spare Part Installed'
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
