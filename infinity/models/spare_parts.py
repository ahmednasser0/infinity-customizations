from odoo import api, fields, models


class SpareRequested(models.Model):
    _name = 'infinity.technical.report.spare.requested'
    _description = 'Technical Report Spare Part Requested'
    _order = 'report_id, id'

    report_id = fields.Many2one(
        'infinity.technical.report', string='Technical Report',
        required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='P/N', required=True)

    # The product's own name, shown beside the part number.
    #
    # Written as a compute rather than related='product_id.display_name':
    # display_name is computed and unstored on every model, and a dependency
    # that runs through one of those has Odoo warning on every write to the
    # records behind it. Depending on the product itself says the same thing
    # and keeps quiet - the field is unstored, so it is worked out afresh on
    # every read anyway.
    description = fields.Char(string='Description', compute='_compute_description')

    @api.depends('product_id')
    def _compute_description(self):
        for line in self:
            line.description = line.product_id.display_name

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

    # See SpareRequested.description above for why this is not a related.
    description = fields.Char(string='Description', compute='_compute_description')

    @api.depends('product_id')
    def _compute_description(self):
        for line in self:
            line.description = line.product_id.display_name

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
