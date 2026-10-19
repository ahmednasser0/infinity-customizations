def migrate(cr, version):
    """Drop the eleven copied checkbox columns on Sales Orders.

    What the contract includes is read straight off the contract now, so the
    order keeps no copy of it. Odoo leaves the column behind when a field
    stops being stored, and the values in these ones are the blanks that had
    the Agreement showing nothing.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.tables WHERE table_name = 'sale_order'
    """)
    if not cr.fetchone():
        return

    for column in ('service_contract_unlimited_em_visits',
                   'service_contract_spare_parts',
                   'service_contract_pm_parts',
                   'service_contract_consumables_including_image_unit',
                   'service_contract_consumables_excluding_image_unit',
                   'service_contract_plain_media',
                   'service_contract_pre_printed_media',
                   'service_contract_operators',
                   'service_contract_owned_machines',
                   'service_contract_site',
                   'service_contract_machines_rent'):
        cr.execute(
            'ALTER TABLE sale_order DROP COLUMN IF EXISTS "%s"' % column)
