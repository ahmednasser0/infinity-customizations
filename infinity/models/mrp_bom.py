from odoo import api, fields, models


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    # Which component of a kit is the machine itself. A kit is sold as one
    # thing but is built of many, and only one of them carries the serial
    # number the service contract is about - this says which.
    engine = fields.Boolean(
        string='Engine',
        help='Tick the one component that is the machine itself. Its serial '
             'number is the one taken onto the Sales Order.')


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    # Which component was ticked last, so that the next tick knows which of
    # the two is the new one. Comparing against what is saved is not enough:
    # tick A, tick B, then tick A again, and A still looks like the saved
    # one - so it would be the tick that gets cleared, every time.
    engine_memo = fields.Char(string='Engine (technical)', copy=False)

    @api.onchange('bom_line_ids')
    def _onchange_bom_line_ids_engine(self):
        """Ticking one component unticks whichever was ticked before.

        This has to sit on the Bill of Materials rather than on the line:
        an onchange on a line returns that line alone, so clearing the tick
        on a sibling there never reaches the screen. From here the whole
        table goes back, and the tick is seen to move.
        """
        ticked = self.bom_line_ids.filtered('engine')
        if len(ticked) > 1:
            held = ticked.filtered(
                lambda line: str(line.product_id.id) == (self.engine_memo or ''))
            keep = (ticked - held)[-1:] or ticked[-1:]
            (ticked - keep).engine = False
            ticked = keep
        memo = str(ticked.product_id.id) if ticked else ''
        if memo != (self.engine_memo or ''):
            self.engine_memo = memo
