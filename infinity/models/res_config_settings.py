from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """The company's choices, on the Settings page.

    Settings is a form over a record that is thrown away when it is saved,
    so nothing can be kept on it. Each field here is a window onto the
    company, where the value actually lives.
    """
    _inherit = 'res.config.settings'

    infinity_consumption_picking_type_id = fields.Many2one(
        related='company_id.infinity_consumption_picking_type_id',
        readonly=False)
