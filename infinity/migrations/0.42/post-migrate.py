from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Work out the machine serial again on every Technical Report.

    The serial is stored, and it is stored the moment the report is made -
    which is when the task is created, before the machine has been sold or
    picked. Reports made then hold a blank, and a blank is invisible to the
    visit history: it looks the machine up by that number.

    The report refreshes itself when it is opened or printed, so the ones
    somebody has been to are right. These are the rest.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    reports = env['infinity.technical.report'].search([
        ('report_type', '=', 'technical_report'),
    ])
    if not reports:
        return
    reports._compute_machine_serial_number()
    env.flush_all()
