from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    actual_engineer_ids = fields.Char(string='Actual Engineer ID', copy=False)

    @api.constrains('actual_engineer_ids')
    def _check_actual_engineer_ids_unique(self):
        for employee in self:
            if not employee.actual_engineer_ids:
                continue
            duplicate = self.with_context(active_test=False).search([
                ('actual_engineer_ids', '=', employee.actual_engineer_ids),
                ('id', '!=', employee.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'The Actual Engineer ID "%(code)s" is already used by %(employee)s.',
                    code=employee.actual_engineer_ids,
                    employee=duplicate.name,
                ))

    @api.depends('actual_engineer_ids', 'name')
    @api.depends_context('show_actual_engineer_id')
    def _compute_display_name(self):
        """Show employees by their Actual Engineer ID where a field asks for
        it through the context, leaving every other employee dropdown in
        Odoo showing the name as usual.

        Overriding the compute replaces its dependencies too, so both fields
        it can display have to be declared here - without them the name
        never refreshes when the ID is set or changed.
        """
        if not self.env.context.get('show_actual_engineer_id'):
            return super()._compute_display_name()
        for employee in self:
            employee.display_name = employee.actual_engineer_ids or employee.name

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Let a field asking for engineer IDs search by the ID as well, so
        typing a code finds its engineer."""
        if name and self.env.context.get('show_actual_engineer_id'):
            domain = list(domain or [])
            matches = self.search(
                domain + [('actual_engineer_ids', operator, name)], limit=limit, order=order)
            if matches:
                return matches._as_query(order)
        return super()._name_search(name, domain, operator, limit, order)
