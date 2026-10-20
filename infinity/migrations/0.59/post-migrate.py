from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Work out the machine serial again, now that the order comes first.

    Until this version the contract's hand-typed number was asked before
    the order's, so a report whose contract carried an old number kept it
    and never saw the serial the machine actually went out under. The
    answer changes for those reports, and it is stored, so it has to be
    asked again rather than waited for.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    reports = env['infinity.technical.report'].search([
        ('report_type', '=', 'technical_report'),
    ])
    if not reports:
        return
    reports._compute_machine_serial_number()
    env.flush_all()
