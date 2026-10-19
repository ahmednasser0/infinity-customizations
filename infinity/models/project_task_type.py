from odoo import api, models

# Odoo keeps a user's own stages - Inbox, Today, This Week and the rest - in
# this same table, told apart by having a Stage Owner. They belong to that
# person's My Tasks and to no project at all, so nothing here touches them.


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    @api.model_create_multi
    def create(self, vals_list):
        """A new project stage belongs to every project there is.

        A stage with no project against it shows up in none of them, not in
        all of them - Odoo reads that list as the stage's whole audience. So
        a stage made anywhere is given every project, which is what makes it
        appear everywhere.
        """
        stages = super().create(vals_list)
        shared = stages.filtered(lambda stage: not stage.user_id)
        if not shared:
            return stages
        projects = self.env['project.project'].search([])
        if projects:
            shared.write({'project_ids': [(4, project.id) for project in projects]})
        return stages
