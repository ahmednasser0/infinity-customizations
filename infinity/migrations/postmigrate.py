import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Drop the stored Contract Type identity columns, and refill the orders
    whose contract details never made it into the snapshot.

    Full Name, Abbreviation and the SLA Sub Type value are read straight off
    the chosen contract now, so their columns hold nothing but the blanks
    that sent us looking. Odoo leaves a column behind when a field stops
    being stored, so they are dropped here.

    Orders that picked a contract but hold none of its terms are then filled
    in as picking it today would fill them. Only those: an order carrying any
    of its own terms is left alone, since the terms on an order are the
    user's to edit and must not be overwritten.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.tables WHERE table_name = 'sale_order'
    """)
    if not cr.fetchone():
        return

    for column in ('service_contract_full_name',
                   'service_contract_abbreviation',
                   'service_contract_sub_type_value'):
        cr.execute(
            'ALTER TABLE sale_order DROP COLUMN IF EXISTS "%s"' % column)

    # Filling old orders back in is a convenience, not the point of this
    # migration - so it runs inside a savepoint. A module left half-upgraded
    # because a nicety failed is a far worse outcome than a few orders still
    # waiting to be filled.
    cr.execute('SAVEPOINT infinity_refill')
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        orders = env['sale.order'].search([('service_contract_id', '!=', False)])
        untouched = orders.filtered(lambda order: not (
            order.service_contract_from_date
            or order.service_contract_to_date
            or order.service_contract_machine_serial_number
            or order.service_contract_sla
        ))
        if untouched:
            untouched._compute_from_service_contract()
            untouched.flush_recordset()
    except Exception:
        cr.execute('ROLLBACK TO SAVEPOINT infinity_refill')
        _logger.warning(
            'infinity: could not refill the contract snapshot on older Sales '
            'Orders; the upgrade carries on without it.', exc_info=True)
    else:
        cr.execute('RELEASE SAVEPOINT infinity_refill')
