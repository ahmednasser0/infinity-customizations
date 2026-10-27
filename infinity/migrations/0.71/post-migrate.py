from odoo import SUPERUSER_ID
from odoo.api import Environment

from odoo.addons.infinity.hooks import set_timesheet_timer_exact


def migrate(cr, version):
    """Turn the timer's rounding off on a database that already has it on.

    post_init_hook only runs when a module is installed, and this one is
    long past that everywhere it is on - so the two parameters would sit at
    15 on exactly the databases that have been writing fifteen-minute
    visits down.
    """
    set_timesheet_timer_exact(Environment(cr, SUPERUSER_ID, {}))
