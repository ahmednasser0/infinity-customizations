from odoo import SUPERUSER_ID
from odoo.api import Environment

_ALLOW_ON_NEW_PROJECTS = (
    'allow_recurring_tasks',
    'allow_milestones',
    'allow_billable',
    'is_fsm',
    'allow_material',
)


def migrate(cr, version):
    """Turn the allowances on for the projects that are already here.

    Up to now they were a default, so they only reached projects made after
    the module went on, and anybody could take one back off. They are fixed
    at yes from this version, which has to mean the projects that already
    exist too - otherwise 'always on' would describe next week's projects
    and nothing in the database today.

    Each field is written on its own, and only to the projects that are
    missing it: is_fsm makes a project a Field Service project and brings
    its own setting-up with it, which is not something to hand the whole
    table at once if it has already been done.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    projects = env['project.project'].with_context(active_test=False)
    for name in _ALLOW_ON_NEW_PROJECTS:
        if name not in projects._fields:
            continue
        missing = projects.search([(name, '=', False)])
        if missing:
            missing.write({name: True})
    env.flush_all()
