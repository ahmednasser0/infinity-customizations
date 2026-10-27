def migrate(cr, version):
    """Mark the reports that were already closed out as closed out.

    The form greys itself from visit_closed, and the flag arrives with this
    version - so without this every report finished before today would open
    editable, however long ago its Task Status was answered.

    A status and no flag is the whole test. No time is invented for them:
    visit_end stays empty on these, because nobody knows when they were
    closed and guessing would put a number on the screen that nothing
    stands behind.
    """
    cr.execute("""
        UPDATE infinity_technical_report
           SET visit_closed = TRUE
         WHERE task_status IS NOT NULL
           AND COALESCE(visit_closed, FALSE) = FALSE
    """)
    cr.execute("""
        UPDATE infinity_technical_report
           SET visit_closed = FALSE
         WHERE visit_closed IS NULL
    """)
