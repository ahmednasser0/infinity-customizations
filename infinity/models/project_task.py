from odoo import _, api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Enable chatter tracking on the existing Dispatcher field (user_ids)
    # NOTE: use an int sequence rather than tracking=True - on this Odoo
    # build passing the bare boolean breaks ir.model.fields reflection
    # (InvalidTextRepresentation: invalid input syntax for type integer: "true")
    user_ids = fields.Many2many(tracking=10)

    pre_dispatch_ids = fields.Many2many(
        'hr.employee',
        'project_task_pre_dispatch_employee_rel',
        'task_id',
        'employee_id',
        string='Planned Engineer',
        help='Pre Dispatch Assignees',
        tracking=20,
    )
    hard_dispatch_id = fields.Many2one(
        'hr.employee',
        string='Actual Engineer',
        help='Hard Dispatch Assignee',
        tracking=30,
    )
    # The Actual Engineer's own ID, filled in as soon as one is chosen above
    # and not editable by hand. It stays a Many2one to hr.employee - the view
    # passes show_actual_engineer_id so it displays the code rather than the
    # name (see hr_employee.py).
    actual_engineer_id_code = fields.Many2one(
        'hr.employee',
        string='Actual Engineer ID',
        compute='_compute_actual_engineer_id_code',
        store=True,
    )

    @api.depends('hard_dispatch_id', 'hard_dispatch_id.actual_engineer_ids')
    def _compute_actual_engineer_id_code(self):
        for task in self:
            engineer = task.hard_dispatch_id
            task.actual_engineer_id_code = engineer if engineer.actual_engineer_ids else False

    fse_accompany_id = fields.Many2one(
        'hr.employee',
        string='FSE Accompany',
        tracking=40,
    )

    visit_type = fields.Selection([
        ('pm', 'PM'),
        ('emergency', 'EM'),
        ('rv', 'RV'),
        ('labor', 'Labor'),
        ('installation', 'Installation'),
        ('inspection', 'Inspection'),
        ('work_shop', 'Work Shop'),
        ('site_survey', 'Site Survey'),
    ], string='Visit Type', required=True)

    # --- Visit count ------------------------------------------------------
    # PM, EM and RV are the visits a contract is measured in, so those are
    # the ones worth counting. The rest are still available on a task, they
    # just carry no allowance to count against.
    COUNTED_VISIT_TYPES = ('pm', 'emergency', 'rv')

    # Each counted visit type spends the contract's allowance of its own
    # kind: a PM visit comes off Limited PM Visits, and so on. The field
    # named here is the one carried on the Sales Order's copy of the
    # contract, so the allowance is the one that order was sold with.
    VISIT_ALLOWANCE_FIELD = {
        'pm': 'service_contract_limited_pm_visits',
        'emergency': 'service_contract_limited_em_visits',
        'rv': 'service_contract_limited_rv_visits',
    }
    # EM alone can be sold without a limit at all.
    VISIT_UNLIMITED_FIELD = {
        'emergency': 'service_contract_unlimited_em_visits',
    }

    visit_count = fields.Integer(
        string='Visits', compute='_compute_visit_count')
    visit_over_allowance = fields.Boolean(
        string='Over the Allowance', compute='_compute_visit_count')
    visit_count_display = fields.Char(
        string='Visits Used', compute='_compute_visit_count')
    visit_count_label = fields.Char(
        string='Visits Label', compute='_compute_visit_count')

    def _visit_allowance(self):
        """How many visits of this task's type the contract allows, as
        (allowed, unlimited).

        Read off the Sales Order's own copy of the contract, so an allowance
        edited on one order applies to that order's visits. allowed is 0
        where there is no contract behind the task, or none covering this
        kind of visit.
        """
        self.ensure_one()
        if self.visit_type not in self.COUNTED_VISIT_TYPES:
            return 0, False
        order = self._infinity_sale_order()
        if not order:
            return 0, False
        unlimited_field = self.VISIT_UNLIMITED_FIELD.get(self.visit_type)
        if unlimited_field and order[unlimited_field]:
            return 0, True
        return order[self.VISIT_ALLOWANCE_FIELD[self.visit_type]], False

    @api.depends('visit_type', 'project_id', 'partner_id')
    def _compute_visit_count(self):
        labels = dict(self._fields['visit_type'].selection)
        for task in self:
            counted = task.visit_type in task.COUNTED_VISIT_TYPES
            allowed, unlimited = task._visit_allowance()

            used = len(task._visit_siblings())
            task.visit_count = used
            task.visit_over_allowance = bool(allowed) and used > allowed

            if not counted:
                task.visit_count_display = str(used)
            elif unlimited:
                task.visit_count_display = _('%s / Unlimited', used)
            elif allowed:
                task.visit_count_display = '%s / %s' % (used, allowed)
            else:
                # no contract behind this task, or none that allows this
                # kind of visit - count them, but against nothing
                task.visit_count_display = str(used)

            if not counted:
                task.visit_count_label = _('Visits')
            elif task.visit_over_allowance:
                task.visit_count_label = _(
                    '%s Visits - Over Limit', labels.get(task.visit_type))
            else:
                task.visit_count_label = _('%s Visits', labels.get(task.visit_type))

    def _visit_siblings(self):
        """Every task standing for a visit of this task's type - this one
        included - for the same customer on the same project.

        A visit only means something against the contract it is spent on, so
        the count is kept to the project and customer the task belongs to
        rather than every task of that type in the database.
        """
        self.ensure_one()
        project = self.project_id._origin
        if self.visit_type not in self.COUNTED_VISIT_TYPES or not project:
            return self.env['project.task']

        domain = [
            ('visit_type', '=', self.visit_type),
            ('project_id', '=', project.id),
        ]
        partner = self.partner_id._origin
        if partner:
            domain.append(('partner_id', '=', partner.id))
        return self.env['project.task'].search(domain)

    def action_open_visit_count(self):
        """List the visits behind the number on the button."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.visit_count_label,
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self._visit_siblings().ids)],
            'context': {'create': False},
        }

    @api.onchange('visit_type')
    def _onchange_visit_allowance(self):
        """Say so, there and then, when this visit takes the contract past
        its allowance.

        A warning, never a refusal: nothing here stops the task being saved,
        an extra visit is a real thing that happens - it just should not pass
        unnoticed.

        Raised only when the visit type itself is picked. Watching the
        project and the customer as well meant the dialog came back on every
        edit that touched them, which is no warning at all - it is a door in
        the way of saving.
        """
        if self.visit_type == self._origin.visit_type:
            return
        allowed, unlimited = self._visit_allowance()
        if not allowed or unlimited:
            return

        siblings = self._visit_siblings()
        used = len(siblings)
        if self._origin not in siblings:
            # this one is about to join them
            used += 1
        if used <= allowed:
            return

        label = dict(self._fields['visit_type'].selection).get(self.visit_type)
        return {
            'warning': {
                # a notification, not a modal: it appears in the corner and
                # fades, leaving the form - and the Save button - alone
                'type': 'notification',
                'title': _('Visit allowance exceeded'),
                'message': _(
                    'The contract allows %(allowed)s %(visit_type)s visits, and '
                    'this one makes %(used)s.\n\n'
                    'Saving is still possible - the extra visits are simply not '
                    'covered by the contract.',
                    allowed=allowed,
                    visit_type=label,
                    used=used,
                ),
            },
        }

    bear_labor_cost = fields.Boolean(string='Bear Labor Cost')
    labor_cost_account_id = fields.Many2one('account.account', string='Labor Cost Account')
    clearing_account_id = fields.Many2one('account.account', string='Clearing Account')

    technical_report_ids = fields.One2many(
        'infinity.technical.report', 'task_id', string='Technical Reports')

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            self.env['infinity.technical.report'].create([
                {'name': 'Agreement', 'task_id': task.id, 'report_type': 'agreement'},
                {'name': 'Visit History', 'task_id': task.id, 'report_type': 'visit_history'},
                {'name': 'Technical Report', 'task_id': task.id, 'report_type': 'technical_report'},
            ])
        return tasks

    def _get_technical_report(self, report_type, name):
        """Return this task's report of the given type, creating it if the
        task predates the module (or the record was deleted)."""
        self.ensure_one()
        report = self.technical_report_ids.filtered(
            lambda r: r.report_type == report_type)[:1]
        if not report:
            report = self.env['infinity.technical.report'].create({
                'name': name,
                'task_id': self.id,
                'report_type': report_type,
            })
        return report

    def action_open_agreement(self):
        self.ensure_one()
        agreement = self._get_technical_report('agreement', 'Agreement')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agreement',
            'res_model': 'infinity.technical.report',
            'view_mode': 'form',
            'views': [(self.env.ref('infinity.infinity_technical_report_view_form_agreement').id, 'form')],
            'res_id': agreement.id,
            'target': 'current',
            'context': {
                'default_task_id': self.id,
                'default_report_type': 'agreement',
                'create': False,
                'delete': False,
                'default_name': 'Agreement',
            },
        }

    def action_open_technical_report(self):
        self.ensure_one()
        report = self._get_technical_report('technical_report', 'Technical Report')
        # The Sales Order may have gained or lost a machine since this report
        # was last looked at, and the form itself cannot add lines.
        report._sync_machine_data()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Technical Report',
            'res_model': 'infinity.technical.report',
            'view_mode': 'form',
            'views': [(self.env.ref('infinity.infinity_technical_report_view_form_technical_report').id, 'form')],
            'res_id': report.id,
            'target': 'current',
            'context': {
                'default_task_id': self.id,
                'default_report_type': 'technical_report',
                'create': False,
                'delete': False,
                'default_name': 'Technical Report',
            },
        }

    def action_open_visit_history(self):
        self.ensure_one()
        visit_history = self._get_technical_report('visit_history', 'Visit History')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Visit History',
            'res_model': 'infinity.technical.report',
            'view_mode': 'form',
            'views': [(self.env.ref('infinity.infinity_technical_report_view_form_visit_history').id, 'form')],
            'res_id': visit_history.id,
            'target': 'current',
            'context': {
                'default_task_id': self.id,
                'default_report_type': 'visit_history',
                'create': False,
                'delete': False,
                'default_name': 'Visit History',
            },
        }

    # --- Contract ---------------------------------------------------------
    # A task's contract terms come from the Sales Order of its project. The
    # lookup lives here rather than on the Agreement, which reads it through
    # infinity.technical.report._find_sale_order().

    def _infinity_sale_order(self):
        """The Sales Order behind this task's project, for this task's
        customer.

        The task, its project and the order all have to be for the same
        customer. A task raised for somebody else is not covered by that
        project's contract, so nothing is returned at all rather than
        somebody else's contract.

        Odoo links a project and a sale order through several different
        fields depending on which modules are installed and how the link was
        made, so try each one rather than assuming a particular setup.
        """
        self.ensure_one()
        SaleOrder = self.env['sale.order']
        project = self.project_id._origin
        partner = self.partner_id._origin
        # The one customer all three must name. Compared by company rather
        # than by the exact partner record: a task for a contact and an order
        # for the company that contact belongs to are the same customer.
        customer = partner.commercial_partner_id
        if not project or not partner or customer != project.partner_id.commercial_partner_id:
            return SaleOrder

        def theirs(order):
            """The order, but only if it is this customer's."""
            return order if order.partner_id.commercial_partner_id == customer else SaleOrder

        # a) the order points at the project. Only stored fields can be
        # searched - sale.order.project_ids, for one, is computed and not
        # stored, and searching it raises.
        for field_name in ('project_id', 'project_ids'):
            field = SaleOrder._fields.get(field_name)
            if field is None or not field.store:
                continue
            order = SaleOrder.search([
                (field_name, '=', project.id),
                ('partner_id', 'child_of', customer.id),
            ], limit=1)
            if order:
                return order

        # b) the project points at the order
        if 'sale_order_id' in project._fields and project.sale_order_id:
            order = theirs(project.sale_order_id)
            if order:
                return order

        # c) the project points at an order line
        if 'sale_line_id' in project._fields and project.sale_line_id:
            order = theirs(project.sale_line_id.order_id)
            if order:
                return order

        # d) last resort - the link field is computed and unsearchable, so
        # read it per order rather than searching on it. Bounded to this
        # customer's orders to keep it cheap.
        for field_name in ('project_id', 'project_ids'):
            if field_name not in SaleOrder._fields:
                continue
            for order in SaleOrder.search([('partner_id', 'child_of', customer.id)]):
                if project in order[field_name]:
                    return order

        return SaleOrder
