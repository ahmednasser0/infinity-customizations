from odoo import _, api, models
from odoo.exceptions import UserError

# On for every project, and not to be turned off. Every one of them is
# Boolean, so 'required' cannot mean what it means on a text box - an empty
# tick is a real answer, and no constraint is broken by it. What it means
# here is that yes is the only answer: they start ticked and unticking one
# is refused.
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

    def write(self, vals):
        """Refuse to turn any of them off.

        A check by @api.constrains cannot be used: it names its fields at
        load time, and is_fsm and allow_material are not there at all unless
        Field Service is installed - naming a field that does not exist stops
        the module loading. Asked here instead, of whatever is actually being
        written.
        """
        off = [
            name for name in _ALLOW_ON_NEW_PROJECTS
            if name in self._fields and name in vals and not vals[name]
        ]
        if off:
            labels = ', '.join(self._fields[name].string for name in off)
            raise UserError(_(
                'These cannot be turned off on a project: %(fields)s.',
                fields=labels))
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Start a project with the allowances on, and with every stage.

        Set rather than defaulted: these are not to be off, so a no arriving
        from an import or a project template is corrected rather than kept.
        A project that reaches the database with one of them off would be a
        project nobody could later fix without tripping the check below.
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
