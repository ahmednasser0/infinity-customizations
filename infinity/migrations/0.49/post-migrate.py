from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Take the projects back off everybody's personal stages.

    Inbox, Today, This Week and the rest live in the same table as project
    stages, told apart by having a Stage Owner. Version 0.48 swept them into
    every project along with the real ones, and they showed up as stages a
    project had. They belong to one person's My Tasks and to no project, so
    the links are removed - every one of them, not just the ones 0.48 made,
    because a personal stage should carry none.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    personal = env['project.task.type'].search([('user_id', '!=', False)])
    personal = personal.filtered('project_ids')
    if not personal:
        return
    personal.write({'project_ids': [(5, 0, 0)]})
    env.flush_all()
