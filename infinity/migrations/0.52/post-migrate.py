from odoo import SUPERUSER_ID
from odoo.api import Environment

from odoo.addons.infinity.hooks import add_helpdesk_menus


def migrate(cr, version):
    """Hang the Agreements menu under Helpdesk on an upgrade too.

    post_init_hook only runs when a module is installed, and this one is
    long past that on every database it is on.
    """
    add_helpdesk_menus(Environment(cr, SUPERUSER_ID, {}))
