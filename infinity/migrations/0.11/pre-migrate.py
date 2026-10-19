def migrate(cr, version):
    """Clear the Visit History records away.

    Every task used to carry a third report of type visit_history, a screen
    for picking one earlier visit to look at. The task's Visit History button
    lists the past visits' own Technical Reports now, so the type is gone from
    the model.

    This has to run before the module loads: a Selection field holding a value
    that is no longer on its list crashes the form the moment it is opened, so
    the rows have to go while the old list is still the one in force.

    Nothing here touches ir_model_fields. Odoo clears the metadata of a field
    that has left the model by itself, and deleting those rows by hand is how
    a live field - visit_count, which merely starts with the same letters -
    loses the row the registry is about to look for.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'infinity_technical_report'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        DELETE FROM infinity_technical_report WHERE report_type = 'visit_history'
    """)
