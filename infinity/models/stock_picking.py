from odoo import fields, models


class StockPicking(models.Model):
    """The link back to the Technical Report a transfer came out of.

    Spare parts on a report go one of two ways: the ones ticked Quote are
    charged for and go on a quotation, and the ones left unticked are
    material consumed under the contract and go out on a transfer. This is
    how a report knows which transfers it raised - so pressing the button
    twice opens the one already there instead of sending the parts out
    again.
    """
    _inherit = 'stock.picking'

    infinity_technical_report_id = fields.Many2one(
        'infinity.technical.report', string='Technical Report',
        ondelete='set null', index='btree_not_null', copy=False)
