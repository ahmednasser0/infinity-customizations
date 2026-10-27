from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Offer the contract's IT serial to the reports already here.

    it_serial_number stopped being a computed field in this version and
    became the engineer's to fill in, so nothing recomputes it any more.
    The reports that got a number from 0.70's compute keep it; the ones
    that were empty would stay empty until somebody opened them from the
    task.

    Only the empty ones are touched. A number already on a report is left
    exactly as it is, whether a compute put it there or a person did.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    reports = env['infinity.technical.report'].with_context(
        active_test=False).search([('it_serial_number', '=', False)])
    if not reports:
        return
    reports._infinity_fill_it_serial()
    env.flush_all()
