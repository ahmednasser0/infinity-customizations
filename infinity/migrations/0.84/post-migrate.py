from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Point the quotations already made at the reports that made them.

    sale_quotation_id has been on the report since 0.65, pointing one way.
    The trail on the report reads the other way - every order whose
    infinity_technical_report_id is this report - and that column arrives
    empty in this version, so the orders quoted before today would show on
    no report at all.
    """
    cr.execute("""
        UPDATE sale_order AS so
           SET infinity_technical_report_id = r.id
          FROM infinity_technical_report AS r
         WHERE r.sale_quotation_id = so.id
           AND so.infinity_technical_report_id IS NULL
    """)
    env = Environment(cr, SUPERUSER_ID, {})
    env.flush_all()
