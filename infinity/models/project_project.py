from odoo import api, fields, models

# Ticked on every new project, and marked required where the field is ours
# to mark. A tick is never empty, so required cannot stop a save the way it
# does on a text box - it says the answer matters, and the answer starts as
# yes. Anybody who means no can still say no.
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

    # Marked required so the form says these matter. Only the three that
    # come with this module's own dependencies are named: redefining a field
    # the database has never heard of would not mark it, it would invent it,
    # and is_fsm and allow_material belong to Field Service.
    allow_recurring_tasks = fields.Boolean(required=True)
    allow_milestones = fields.Boolean(required=True)
    allow_billable = fields.Boolean(required=True)

    @api.model
    def default_get(self, fields_list):
        """Show the allowances already ticked on a new project's form.

        create() alone would tick them on save, which is too late to be read
        as a default: the form opens with empty boxes and they fill
        themselves in once the project is gone. Answering here puts the ticks
        on the screen, where somebody can see them and take one off.

        A default handed in deliberately - default_allow_billable in the
        context, say, from a button or a link - is left alone.
        """
        values = super().default_get(fields_list)
        for name in _ALLOW_ON_NEW_PROJECTS:
            if name not in self._fields or name not in fields_list:
                continue
            if 'default_%s' % name in self.env.context:
                continue
            values[name] = True
        return values

    @api.model_create_multi
    def create(self, vals_list):
        """Start a project with the allowances on, and with every stage.

        What came in is left as it was found: a no given deliberately - by
        hand, by an import, by a project template - is the answer somebody
        meant, and is not corrected to yes.
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
