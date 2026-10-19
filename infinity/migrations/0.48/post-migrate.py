from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Put every stage that exists on every project that exists.

    From here on the two create() overrides keep the rule, but they only
    speak for records made after them. This is the one pass over what is
    already there.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    stages = env['project.task.type'].search([])
    projects = env['project.project'].search([])
    if not stages or not projects:
        return
    stages.write({'project_ids': [(4, project.id) for project in projects]})
    env.flush_all()
