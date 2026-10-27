from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Fill in the IT serial on the reports that already exist.

    it_serial_number is stored and is worked out from the order behind the
    report, so until something recomputes it every report in the database
    carries an empty one - including the ones whose contracts have had an
    IT serial typed in since.

    machine_model and manufacturer are not touched. They stopped being
    columns this module reads in this version and became answers off the
    product, so there is nothing of theirs left to recompute. The words
    anybody typed into them are still in those columns, untouched, in case
    they are ever wanted back.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    reports = env['infinity.technical.report'].with_context(
        active_test=False).search([])
    if not reports:
        return
    reports._compute_machine_serial_number()
    env.flush_all()
