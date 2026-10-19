def migrate(cr, version):
    """Drop the three accounting fields the task no longer carries.

    Odoo leaves a column behind when a field is taken off a model, and these
    three were only ever filled in by hand on the task. They are of no use to
    anything now, so the columns go with the fields.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.tables WHERE table_name = 'project_task'
    """)
    if not cr.fetchone():
        return

    for column in ('bear_labor_cost',
                   'labor_cost_account_id',
                   'clearing_account_id'):
        cr.execute(
            'ALTER TABLE project_task DROP COLUMN IF EXISTS "%s"' % column)
