def migrate(cr, version):
    """Tick Quote on every spare part asked for before the box existed.

    A new boolean column arrives NULL on the rows already in the table, and
    NULL reads as false. Left alone, every part ever asked for would read
    as material consumed under the contract - nothing to charge for, and a
    transfer waiting to send all of it out. They were all being quoted, so
    they all say so.

    The field's default only applies to rows written from now on, which is
    why this cannot be left to it.
    """
    cr.execute("""
        UPDATE infinity_technical_report_spare_requested
           SET to_quotation = TRUE
         WHERE to_quotation IS NULL
    """)
