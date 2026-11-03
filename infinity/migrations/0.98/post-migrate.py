from odoo import SUPERUSER_ID
from odoo.api import Environment


def migrate(cr, version):
    """Work the stored answers out again for the reports already here.

    Three of the fields on a Technical Report are stored computes whose
    triggers are field paths: the Sales Order, the machine's model and its
    make. None of those paths changes during an upgrade, so the reports
    already in the database would keep whatever they were last computed
    with - which for every one of them is nothing, because until this
    version the lookups were asking the wrong questions:

      - a Technical Report's order was its own guess from the task's
        project, which outranked the one picked by hand on the task's
        Agreement. Where the guess landed on another of that customer's
        orders, every contract term on the report read as zero.
      - the machine was reached through the lot on the order line, which
        belongs to the Engine, and then asked for its own Engine

    Both are answered now, so the answers are taken afresh here. The
    contract terms on a report - Max Copies among them - are unstored and
    need nothing: they read the order on every open.
    """
    env = Environment(cr, SUPERUSER_ID, {})
    Report = env['infinity.technical.report'].with_context(active_test=False)
    reports = Report.search([])
    if reports:
        # The order first and on its own: the machine is looked up through
        # it, so recomputing both at once would read the order as it was.
        reports.invalidate_recordset(['agreement_sale_order_id'])
        reports.modified(['task_id'])
        reports._compute_agreement_sale_order()
        reports.flush_recordset()

        reports._compute_machine_details()
        reports.flush_recordset()

    contracts = env['infinity.service.contract'].search([])
    if contracts:
        contracts._compute_machine_details()
        contracts.flush_recordset()

    env.flush_all()
