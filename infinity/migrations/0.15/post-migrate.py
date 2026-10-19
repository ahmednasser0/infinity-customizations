def migrate(cr, version):
    """Carry across what the four changes of shape left behind.

    The serials drop the month, the order number moves to the task, the
    readings move off their own lines and onto the report, and the fax leaves
    contacts for the company.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'infinity_technical_report'
    """)
    if not cr.fetchone():
        return

    _serials_without_the_month(cr)
    _work_order_no_onto_the_task(cr)
    _readings_onto_the_report(cr)
    _fax_off_contacts(cr)


def _has_column(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def _serials_without_the_month(cr):
    """Ahmad-2026-09-000001 becomes Ahmad-2026-000001.

    The numbers already handed out keep their order and their count; only the
    month comes out of the middle of them.
    """
    cr.execute("""
        SELECT r.id, e.name, r.serial_year, r.serial_counter
        FROM infinity_technical_report r
        JOIN hr_employee e ON e.id = r.serial_engineer_id
        WHERE r.report_type = 'technical_report'
          AND r.serial_number IS NOT NULL
          AND r.serial_year > 0
          AND r.serial_counter > 0
    """)
    for record_id, name, year, counter in cr.fetchall():
        cr.execute(
            "UPDATE infinity_technical_report SET serial_number = %s WHERE id = %s",
            ('%s-%s-%06d' % ((name or '').strip(), year, counter), record_id))


def _work_order_no_onto_the_task(cr):
    """The number was typed on the report; it belongs to the task now.

    A task takes the number from its own Technical Report, and only where it
    has none of its own. The report's column is then dropped: the field
    behind it reads the task.
    """
    if not _has_column(cr, 'infinity_technical_report', 'work_order_no'):
        return
    cr.execute("""
        UPDATE project_task t
        SET work_order_no = r.work_order_no
        FROM infinity_technical_report r
        WHERE r.task_id = t.id
          AND r.report_type = 'technical_report'
          AND r.work_order_no IS NOT NULL
          AND r.work_order_no <> ''
          AND (t.work_order_no IS NULL OR t.work_order_no = '')
    """)
    cr.execute(
        'ALTER TABLE infinity_technical_report DROP COLUMN IF EXISTS work_order_no')


def _readings_onto_the_report(cr):
    """One report, one machine - so the first line's readings come up onto it.

    Reports that carried more than one machine keep only the first, by the
    order the lines were made in. The old table is left where it is rather
    than emptied here: Odoo drops it when it clears away the model, and until
    then it is the only copy of anything a second line held.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'infinity_machine_data'
    """)
    if not cr.fetchone():
        return
    # What was written down by hand comes across as it stands. The serial
    # is only filled where the report worked none out for itself: that one
    # is computed from the orders, and the computed answer is the newer.
    cr.execute("""
        UPDATE infinity_technical_report r
        SET machine_model   = m.machine_model,
            manufacturer    = m.manufacturer,
            service_counter = m.service_counter,
            total_counter   = m.total_counter,
            color_counter   = m.color_counter,
            black_counter   = m.black_counter
        FROM (
            SELECT DISTINCT ON (report_id) *
            FROM infinity_machine_data
            ORDER BY report_id, id
        ) m
        WHERE m.report_id = r.id
    """)
    cr.execute("""
        UPDATE infinity_technical_report r
        SET machine_serial_number = m.machine_serial_number
        FROM (
            SELECT DISTINCT ON (report_id) *
            FROM infinity_machine_data
            ORDER BY report_id, id
        ) m
        WHERE m.report_id = r.id
          AND COALESCE(r.machine_serial_number, '') = ''
          AND COALESCE(m.machine_serial_number, '') <> ''
    """)


def _fax_off_contacts(cr):
    """The field sits on the company now, so the contacts' column goes."""
    cr.execute('ALTER TABLE res_partner DROP COLUMN IF EXISTS fax')
