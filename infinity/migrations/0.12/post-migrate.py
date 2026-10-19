def migrate(cr, version):
    """Carry the single FSE Accompany over into the new list.

    The field was a Many2one and is a Many2many now, so the value moves from
    a column on the task to a row in a relation table. This runs after the
    module has loaded, when that table exists.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_task' AND column_name = 'fse_accompany_id'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'project_task_fse_accompany_employee_rel'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        INSERT INTO project_task_fse_accompany_employee_rel (task_id, employee_id)
        SELECT id, fse_accompany_id
        FROM project_task
        WHERE fse_accompany_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)
    cr.execute('ALTER TABLE project_task DROP COLUMN IF EXISTS fse_accompany_id')
