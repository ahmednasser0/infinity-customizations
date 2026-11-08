from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Join the quotation lines the button made back to their spare parts.

    infinity_spare_line_id is what ties a quotation line to the requested
    part that asked for it. Every path that quotes a part wrote it except
    the Set to Quotation button, which left it empty - so on a quotation
    that button had made, unticking Quote took nothing off the quotation
    and editing a quantity reached nothing.

    The button writes it now. The quotations already made are paired up
    here, by product, within one report's own quotation: a line is matched
    to a part asking for that product and then set aside, so two lines for
    the same product take one part each rather than both taking the first.
    A pairing by product is a guess, but it is a guess over the few lines
    of one quotation, and the alternative is leaving them joined to
    nothing at all.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    Report = env['infinity.technical.report'].with_context(active_test=False)
    for report in Report.search([('sale_quotation_id', '!=', False)]):
        free = report.sale_quotation_id.order_line.filtered(
            lambda order_line: not order_line.infinity_spare_line_id)
        if not free:
            continue
        for line in report.spare_requested_ids:
            if not line.product_id:
                continue
            match = free.filtered(
                lambda order_line: order_line.product_id == line.product_id)[:1]
            if not match:
                continue
            match.infinity_spare_line_id = line.id
            free -= match
    env.flush_all()
