from odoo import api, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    @api.model_create_multi
    def create(self, vals_list):
        """A new stage belongs to every project there is.

        A stage with no project against it shows up in none of them, not in
        all of them - Odoo reads that list as the stage's whole audience. So
        a stage made anywhere is given every project, which is what makes it
        appear everywhere.
        """
        stages = super().create(vals_list)
        projects = self.env['project.project'].search([])
        if projects:
            stages.write({'project_ids': [(4, project.id) for project in projects]})
        return stages


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model_create_multi
    def create(self, vals_list):
        """And a new project gets every stage there is.

        The other half of the same rule. Without it the rule would only hold
        looking backwards: stages made today would reach every project, and
        projects made tomorrow would start out missing them.
        """
        projects = super().create(vals_list)
        stages = self.env['project.task.type'].search([])
        if stages:
            stages.write({'project_ids': [(4, project.id) for project in projects]})
        return projects
