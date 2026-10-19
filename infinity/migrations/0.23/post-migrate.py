from odoo import SUPERUSER_ID
from odoo.api import Environment

from odoo.addons.infinity.hooks import add_visit_history_menu


def migrate(cr, version):
    """Make the Helpdesk menu on an upgrade too.

    post_init_hook only runs when a module is installed, and this one is
    long past that on every database it is on.
    """
    add_visit_history_menu(Environment(cr, SUPERUSER_ID, {}))
