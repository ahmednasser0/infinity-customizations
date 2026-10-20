from odoo import api, fields, models

# Always on, on every project. Not a default somebody may take back: the
# answer is fixed at yes, so the form shows them ticked and greyed, and
# anything that writes no - a hand, an import, an API call, another module -
# is corrected back to yes.
#
# Not every one of them is always there: allow_billable comes with
# sale_project, and is_fsm and allow_material with Field Service, so each is
# only set where the model actually carries it.
_ALLOW_ON_NEW_PROJECTS = (
    'allow_recurring_tasks',
    'allow_milestones',
    'allow_billable',
    'is_fsm',
    'allow_material',
)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # Greyed on the form so the tick reads as settled rather than as
    # something to decide. Only the three that come with this module's own
    # dependencies are named: redefining a field the database has never
    # heard of would not mark it, it would invent it, and is_fsm and
    # allow_material belong to Field Service. Those two stay clickable, and
    # write() below puts them back.
    allow_recurring_tasks = fields.Boolean(required=True, readonly=True)
    allow_milestones = fields.Boolean(required=True, readonly=True)
    allow_billable = fields.Boolean(required=True, readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Open a new project's form with the allowances already ticked.

        create() alone would tick them on save, which is too late to be
        seen: the form would open with empty boxes and fill itself in once
        the project is gone. Answering here puts the ticks on the screen.

        A default handed in through the context is not honoured for these,
        the way it would be for a field somebody may still decide: the
        value is fixed, so there is nothing for a caller to pick.
        """
        values = super().default_get(fields_list)
        for name in _ALLOW_ON_NEW_PROJECTS:
            if name in self._fields and name in fields_list:
                values[name] = True
        return values

    @api.model_create_multi
    def create(self, vals_list):
        """Start every project with the allowances on, and with every stage.

        A no that came in - by hand, by an import, by a project template -
        is overwritten rather than respected: these are not questions this
        module leaves open.
        """
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            for name in _ALLOW_ON_NEW_PROJECTS:
                if name in self._fields:
                    vals[name] = True

        projects = super().create(vals_list)

        # the other half of 'every stage on every project' - see
        # project_task_type.py for the half that runs when a stage is made
        stages = self.env['project.task.type'].search([('user_id', '=', False)])
        if stages:
            stages.write({'project_ids': [(4, project.id) for project in projects]})
        return projects

    def write(self, vals):
        """Keep the allowances on, whatever a write asks for.

        Only the ones a write actually mentions are corrected. Leaving the
        rest alone keeps an ordinary edit - a rename, a new deadline - from
        dragging five extra fields through the save with it.
        """
        asked_off = [
            name for name in _ALLOW_ON_NEW_PROJECTS
            if name in vals and not vals[name] and name in self._fields
        ]
        if asked_off:
            vals = dict(vals)
            for name in asked_off:
                vals[name] = True
        return super().write(vals)
