from odoo import SUPERUSER_ID
from odoo.api import Environment

from odoo.addons.infinity.hooks import claim_ts_labor_sequence


def migrate(cr, version):
    """Settle the TS-LABOR sequence on a database that already has one.

    post_init_hook only runs when a module is installed, and this one is
    long past that everywhere it is on. The sequence arrives with this
    version, so the database it arrives on is exactly the one that may
    already have a hand-made sequence of the same code to stand down.
    """
    claim_ts_labor_sequence(Environment(cr, SUPERUSER_ID, {}))
