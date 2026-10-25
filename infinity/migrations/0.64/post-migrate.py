def migrate(cr, version):
    """Make sure the reports that were here before are not archived.

    Odoo fills a new column's default in for the rows already in the table,
    so this should already be true. It is written out anyway because of what
    the alternative looks like: active NULL reads as archived, and every
    Technical Report and Agreement in the database would quietly vanish from
    its screen. Three lines against that is a bargain, and running them
    twice costs nothing.
    """
    cr.execute("""
        UPDATE infinity_technical_report
           SET active = TRUE
         WHERE active IS NULL
    """)
