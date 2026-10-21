"""Hanging this module's lists under Helpdesk, without depending on Helpdesk.

Helpdesk is not in this module's dependencies and may not be installed at
all, so its menus cannot be named in XML: an XML ID that is not there stops
the whole module from loading. The menus are made here instead, from
whatever Helpdesk turns out to have, and where Helpdesk is absent nothing
is made and nothing breaks.
"""

# The menus to hang, as (our own XML ID, label, the action it opens).
MENUS = (
    ('menu_infinity_visit_history_helpdesk', 'Visits History',
     'infinity.infinity_action_technical_report'),
    ('menu_infinity_agreement_helpdesk', 'Agreements',
     'infinity.infinity_action_agreement'),
)


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
    # no menu by that name - hang them off Helpdesk itself rather than nowhere
    return menus.filtered(lambda menu: not menu.parent_id)[:1]


def add_helpdesk_menus(env):
    """Put this module's lists under Helpdesk's Tickets, and keep them there.

    Safe to run again: each menu is registered under an XML ID of this
    module's own, so a second run finds it rather than making another.
    """
    parent = _helpdesk_tickets_menu(env)
    if not parent:
        return

    for sequence, (xmlid, label, action_xmlid) in enumerate(MENUS):
        action = env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            continue

        values = {
            'parent_id': parent.id,
            'action': 'ir.actions.act_window,%d' % action.id,
        }
        menu = env.ref('infinity.%s' % xmlid, raise_if_not_found=False)
        if menu:
            menu.write(values)
            continue

        menu = env['ir.ui.menu'].create(dict(
            values, name=label, sequence=50 + sequence))
        env['ir.model.data'].create({
            'module': 'infinity',
            'name': xmlid,
            'model': 'ir.ui.menu',
            'res_id': menu.id,
            'noupdate': True,
        })


# Kept under its old name as well: migration 0.23 calls it by that name, and
# a migration already run on a database must keep working if it is replayed.
add_visit_history_menu = add_helpdesk_menus


# ---------------------------------------------------------------------------
# The TS-LABOR running number
# ---------------------------------------------------------------------------
# data/ir_sequence.xml makes the sequence the automation rules draw from.
# What it cannot do is notice that the database already has one: these rules
# have been running on a sequence somebody made by hand (Settings >
# Technical > Sequences, or Studio), and ir.sequence does not mind two
# records sharing a code. next_by_code picks one of them, ordered by
# company, so the hand-made one can win and the two series drift apart.
#
# So the hand-made one is stood down rather than left to compete: the number
# it had reached is carried over first, because a reference already on a
# posted journal entry must not come round a second time.

_TS_LABOR_CODE = 'ts.labor.ref'


def claim_ts_labor_sequence(env):
    """Make this module's sequence the only one answering to its code.

    Safe to run again: once the others are renamed there is nothing left to
    find, and the second run does nothing.
    """
    ours = env.ref('infinity.seq_ts_labor_ref', raise_if_not_found=False)
    if not ours:
        return

    others = env['ir.sequence'].with_context(active_test=False).search([
        ('code', '=', _TS_LABOR_CODE),
        ('id', '!=', ours.id),
    ])
    if not others:
        return

    # Only the number is taken, not the prefix or the padding: the shape of
    # the reference is the one Accounting asked for and is already in
    # data/ir_sequence.xml. Numbers from a sequence Odoo has retired still
    # count, hence active_test above.
    reached = max(others.mapped('number_next_actual') or [0])
    if reached > ours.number_next_actual:
        ours.number_next_actual = reached

    # Renamed and archived rather than deleted. A sequence that has issued
    # references which are sitting on posted entries is a record of what
    # happened, and deleting it to tidy up throws that away.
    others.write({
        'code': '%s.replaced.by.infinity' % _TS_LABOR_CODE,
        'active': False,
    })


def post_init_hook(env):
    add_helpdesk_menus(env)
    claim_ts_labor_sequence(env)
