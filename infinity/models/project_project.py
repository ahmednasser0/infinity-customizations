from odoo import api, fields, models

# Two sets, because two different things were asked for.
#
# These start ticked on a new project and then belong to whoever is looking
# at the form. A no here is an answer, and it is kept.
_ALLOW_DEFAULT_ON = (
    'allow_recurring_tasks',
    'allow_milestones',
)

# These are not questions. They start ticked, they stay ticked, and anything
# that writes a no - a hand, an import, an API call, another module - is
# corrected back.
#
# Not every one of them is always there: allow_billable comes with
# sale_project, and is_fsm and allow_material with Field Service, so each is
# only touched where the model actually carries it.
_ALLOW_ALWAYS_ON = (
    'allow_billable',
    'is_fsm',
    'allow_material',
)

_ALLOW_ON_NEW_PROJECTS = _ALLOW_DEFAULT_ON + _ALLOW_ALWAYS_ON


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # allow_billable is greyed: it is in the always-on set, and a tick
    # somebody can press that springs back is worse than one they cannot
    # press at all. The other two are left alone - they are defaults now,
    # not rules, so the box has to be a box.
    #
    # Only fields from this module's own dependencies are named here.
    # Redefining one the database has never heard of would not adjust it, it
    # would invent it, and is_fsm and allow_material belong to Field Service.
    # Those two stay clickable and write() below puts them back.
    allow_recurring_tasks = fields.Boolean(required=True)
    allow_milestones = fields.Boolean(required=True)
    allow_billable = fields.Boolean(required=True, readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Open a new project's form with all five already ticked.

        create() alone would tick them on save, which is too late to be
        seen: the form would open with empty boxes and fill itself in once
        the project is gone. Answering here puts the ticks on the screen.

        A default handed in through the context wins for the two that are
        only defaults - a caller asking for something else is making a
        choice, and these are now choices. The always-on three ignore it,
        because there is nothing there to choose.
        """
        values = super().default_get(fields_list)
        for name in _ALLOW_ON_NEW_PROJECTS:
            if name not in self._fields or name not in fields_list:
                continue
            if name in _ALLOW_DEFAULT_ON and 'default_%s' % name in self.env.context:
                continue
            values[name] = True
        return values

    @api.model_create_multi
    def create(self, vals_list):
        """Start every project with the allowances on, and with every stage.

        A no that came in is respected for the two that are defaults and
        overwritten for the three that are not.
        """
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            for name in _ALLOW_DEFAULT_ON:
                if name in self._fields and name not in vals:
                    vals[name] = True
            for name in _ALLOW_ALWAYS_ON:
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
        """Keep the always-on three on, whatever a write asks for.

        Only the ones a write actually mentions are corrected, so an
        ordinary edit - a rename, a new deadline - does not drag three extra
        fields through the save with it. The two defaults are not touched
        here at all: turning one off is the point of them being editable.
        """
        asked_off = [
            name for name in _ALLOW_ALWAYS_ON
            if name in vals and not vals[name] and name in self._fields
        ]
        if asked_off:
            vals = dict(vals)
            for name in asked_off:
                vals[name] = True
        return super().write(vals)
