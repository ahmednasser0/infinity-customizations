from odoo import models


class StopTimerConfirmationWizard(models.Model):
    """The dialog Odoo raises when the timer on a task is stopped.

    models.Model, not TransientModel, despite the word wizard in its name:
    Odoo refuses an extension that would turn a model transient, and this
    one is not. The database said so - "transforms the model ... into a
    transient model" - which is the sort of thing only the database can say
    about a model that lives in Enterprise.

    It offers the measured time for editing. Visit Start and Visit End are
    stamped by code precisely so nobody has to be trusted to type them, and
    letting the hours themselves be corrected on the way out would undo that
    for the one number anybody would want to round.
    """
    _inherit = 'hr.timesheet.stop.timer.confirmation.wizard'

    def fields_get(self, allfields=None, attributes=None):
        """Hand the client a readonly Time Spent.

        Redefining the field here - time_spent = fields.Float(readonly=True) -
        is the usual way to do this, and is not used because it would mean
        restating the field's type. This wizard belongs to timesheet_grid,
        which is Enterprise and not something this module can read, so the
        type would be a guess; getting it wrong replaces the field rather
        than adjusting it. Saying readonly here needs to know only the name,
        which the database already told us.

        The value still reaches the wizard's own button: readonly stops the
        box being typed in, it does not stop the record carrying what the
        timer measured.
        """
        result = super().fields_get(allfields=allfields, attributes=attributes)
        if 'time_spent' in result:
            result['time_spent']['readonly'] = True
        return result
