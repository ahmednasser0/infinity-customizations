"""Hanging Visits History under Helpdesk, without depending on Helpdesk.

Helpdesk is not in this module's dependencies and may not be installed at
all, so its menus cannot be named in XML: an XML ID that is not there stops
the whole module from loading. The menu is made here instead, from whatever
Helpdesk turns out to have, and where Helpdesk is absent nothing is made
and nothing breaks.
"""

MENU_XMLID = 'menu_infinity_visit_history_helpdesk'


def _helpdesk_tickets_menu(env):
    """Helpdesk's Tickets menu, or its root, or nothing at all."""
    data = env['ir.model.data'].search([
        ('module', '=', 'helpdesk'),
        ('model', '=', 'ir.ui.menu'),
    ])
    menus = env['ir.ui.menu'].browse(data.mapped('res_id')).exists()
    if not menus:
        return env['ir.ui.menu']

    tickets = menus.filtered(
        lambda menu: (menu.name or '').strip().lower() == 'tickets'
        and menu.parent_id)
    if tickets:
        return tickets[:1]
    # no menu by that name - hang it off Helpdesk itself rather than nowhere
    return menus.filtered(lambda menu: not menu.parent_id)[:1]


def add_visit_history_menu(env):
    """Put Visits History under Helpdesk's Tickets, and keep it there.

    Safe to run again: the menu is registered under an XML ID of this
    module's own, so a second run finds it rather than making another.
    """
    parent = _helpdesk_tickets_menu(env)
    if not parent:
        return

    action = env.ref('infinity.infinity_action_technical_report',
                     raise_if_not_found=False)
    if not action:
        return

    menu = env.ref('infinity.%s' % MENU_XMLID, raise_if_not_found=False)
    if menu:
        menu.write({'parent_id': parent.id,
                    'action': 'ir.actions.act_window,%d' % action.id})
        return

    menu = env['ir.ui.menu'].create({
        'name': 'Visits History',
        'parent_id': parent.id,
        'action': 'ir.actions.act_window,%d' % action.id,
        'sequence': 50,
    })
    env['ir.model.data'].create({
        'module': 'infinity',
        'name': MENU_XMLID,
        'model': 'ir.ui.menu',
        'res_id': menu.id,
        'noupdate': True,
    })


def post_init_hook(env):
    add_visit_history_menu(env)
