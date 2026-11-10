from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    fax = fields.Char(string='Fax')

    # The operation type Deliver Consumed Materials raises its transfers
    # under. It was a name written into the code - 'Contract Material
    # Consumption', on the 'Konica Minolta Main' warehouse - which meant
    # renaming the operation type, or wanting another one, was a change to
    # the module. It is a choice now, made once in the Inventory settings.
    #
    # On the company rather than in a system parameter: an operation type
    # belongs to a company, so each company has to be able to name its own.
    infinity_consumption_picking_type_id = fields.Many2one(
        'stock.picking.type', string='Consumed Materials Operation Type')
