def migrate(cr, version):
    """Rewrite the serial numbers that were issued in the old shape.

    A number is handed out once and then kept for good, so reports made
    before the format carried the year and the month still read
    'Ahmad-000001'. They are renumbered here, oldest first, so each
    engineer's count for a year runs 1, 2, 3 ... in the order the reports
    were created - which is the order the old numbers ran in too.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'infinity_technical_report'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        SELECT r.id,
               r.serial_engineer_id,
               e.name,
               EXTRACT(YEAR FROM r.create_date)::int,
               EXTRACT(MONTH FROM r.create_date)::int
        FROM infinity_technical_report r
        JOIN hr_employee e ON e.id = r.serial_engineer_id
        WHERE r.report_type = 'technical_report'
          AND r.serial_number IS NOT NULL
        ORDER BY r.id
    """)

    counters = {}
    for record_id, engineer_id, name, year, month in cr.fetchall():
        key = (engineer_id, year)
        counter = counters.get(key, 0) + 1
        counters[key] = counter
        serial = '%s-%s-%02d-%06d' % ((name or '').strip(), year, month, counter)
        cr.execute("""
            UPDATE infinity_technical_report
            SET serial_number = %s, serial_year = %s, serial_counter = %s
            WHERE id = %s
        """, (serial, year, counter, record_id))
