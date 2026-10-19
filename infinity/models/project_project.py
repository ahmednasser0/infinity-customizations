from odoo import api, models

# Ticked on every new project. All four are Boolean, so there is no such
# thing as leaving one unanswered - the question is only which answer a
# project starts with, and here it is yes. Anybody can untick one afterwards.
#
# Not every one of them is always there: allow_billable comes with
# sale_project and allow_material with Field Service, so each is only set
# where the model actually carries it.
_ALLOW_ON_NEW_PROJECTS = (
    'allow_recurring_tasks',
    'allow_milestones',
    'allow_billable',
    'allow_material',
)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model_create_multi
    def create(self, vals_list):
        """Start a project with the four allowances on, and with every stage.

        What came in is left as it was found: a value given explicitly - by
        hand, by an import, by a project template - is the answer somebody
        meant, and is not overwritten with yes.
        """
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            for name in _ALLOW_ON_NEW_PROJECTS:
                if name in self._fields and name not in vals:
                    vals[name] = True

        projects = super().create(vals_list)

        # the other half of 'every stage on every project' - see
        # project_task_type.py for the half that runs when a stage is made
        stages = self.env['project.task.type'].search([('user_id', '=', False)])
        if stages:
            stages.write({'project_ids': [(4, project.id) for project in projects]})
        return projects
