from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # What the time was spent under, for the screens where timesheets are
    # looked over: the SLA Sub Type of the contract behind the work.
    #
    # Not stored. It is read off the Agreement, through a path with no
    # field to watch for changes, so storing it would only be a copy going
    # stale. That makes it a column to read rather than one to sort or
    # filter by. An Agreement with no contract on it leaves this empty.
    infinity_sla_sub_type = fields.Char(
        string='SLA Sub Type', compute='_compute_infinity_sla_sub_type')

    # --- TS-LABOR ---------------------------------------------------------
    # Written by the TS-LABOR automation rules, which live in the database.
    # The x_ prefix is kept on purpose: the rules address these fields by
    # name, and renaming them would stop every one of them working.
    x_ts_audit_log = fields.Text(
        string='Audit Log',
        readonly=True,
        copy=False,
        help='Who edited / validated this timesheet line and when (written by '
             'TS-LABOR rules).',
    )
    x_ts_snapshot = fields.Text(
        string='TS Snapshot',
        readonly=True,
        copy=False,
        help='Technical: last known values '
             '(date|employee|project|task|hours|description) used by the audit '
             'rule to log old -> new changes.',
    )
    x_ts_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Labor Cost Entry',
        readonly=True,
        copy=False,
        index=True,
        ondelete='set null',
        help='Journal entry created when this timesheet line was validated.',
    )

    @api.depends('task_id', 'project_id')
    def _compute_infinity_sla_sub_type(self):
        for line in self:
            agreement = line._infinity_agreement()
            line.infinity_sla_sub_type = (
                agreement.agreement_service_contract_id.name.sla_sub_type
                or False)

    def _infinity_agreement(self):
        """The Agreement this line's work falls under.

        Read off the Agreement rather than worked out again from the Sales
        Order: the Agreement already decides whether there is a contract to
        show - task, project and order all naming one customer - and a
        timesheet must not read a contract the Agreement itself refuses.
        An Agreement showing nothing leaves this blank, which is the answer.

        A line booked to a project with no task takes the first Agreement in
        that project that has a contract on it.
        """
        self.ensure_one()
        Report = self.env['infinity.technical.report']

        if self.task_id:
            return self.task_id.technical_report_ids.filtered(
                lambda report: report.report_type == 'agreement')[:1]

        if not self.project_id:
            return Report

        agreements = Report.search([
            ('report_type', '=', 'agreement'),
            ('task_id.project_id', '=', self.project_id.id),
        ])
        return agreements.filtered('agreement_service_contract_id')[:1]
