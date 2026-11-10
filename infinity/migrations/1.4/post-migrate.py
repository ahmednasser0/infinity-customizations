from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Choose, for each company, the operation type the code used to name.

    Deliver Consumed Materials found its operation type by a name written
    into the module: 'Contract Material Consumption', preferring the one on
    the 'Konica Minolta Main' warehouse. It is a setting now, and a setting
    arrives empty - so without this the button would stop working on
    upgrade until somebody found the new box and filled it in.

    Each company is given what the name would have found for it. One that
    already has a choice keeps it, and one with no such operation type is
    left empty, where the button says what to do.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    PickingType = env['stock.picking.type']
    for company in env['res.company'].search(
            [('infinity_consumption_picking_type_id', '=', False)]):
        found = PickingType.search([
            ('name', '=', 'Contract Material Consumption'),
            ('company_id', '=', company.id),
        ])
        if len(found) > 1:
            found = found.filtered(
                lambda kind: kind.warehouse_id.name == 'Konica Minolta Main'
            ) or found
        if found:
            company.infinity_consumption_picking_type_id = found[:1]
    env.flush_all()
