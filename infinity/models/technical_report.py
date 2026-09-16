from odoo import _, api, fields, models


class TechnicalReport(models.Model):
    _name = 'infinity.technical.report'
    _description = 'Technical Report'

    name = fields.Char(string='Name', required=True, default='Agreement')
    task_id = fields.Many2one(
        'project.task', string='Task', required=True, ondelete='cascade')
    report_type = fields.Selection([
        ('agreement', 'Agreement'),
        ('visit_history', 'Visit History'),
        ('technical_report', 'Technical Report'),
    ], string='Report Type', default='agreement')

    task_name = fields.Char(related='task_id.name', string='Task Name', readonly=True)

    # The customer this agreement is with: the one the selected Sales Order
    # was raised for, falling back to the task's own where no order is
    # picked yet.
    #
    # Worked out on every read rather than stored: a stored value only ever
    # changes when Odoo decides to recompute it, which is how the Agreement
    # ended up holding a customer that had since been changed elsewhere -
    # and how a single empty recompute could leave the field blank for good.
    agreement_partner_id = fields.Many2one(
        'res.partner', string='Customer',
        compute='_compute_agreement_partner')

    def _agreement_source_partner(self):
        """Whoever the contract was sold to - the order's customer, or the
        task's own where no order is picked yet.

        This is the one on the paperwork, which may be a person inside a
        company; the Customer and Contact Person fields split it up from
        here.
        """
        self.ensure_one()
        return (self.agreement_sale_order_id.partner_id
                or self.task_id.partner_id)

    @api.depends('agreement_sale_order_id', 'agreement_sale_order_id.partner_id',
                 'agreement_sale_order_id.partner_id.commercial_partner_id',
                 'task_id.partner_id', 'task_id.partner_id.commercial_partner_id')
    def _compute_agreement_partner(self):
        """A contact inside a company is shown under that company; anyone
        standing on their own is their own customer.

        commercial_partner_id is Odoo's own answer to this: the company a
        contact belongs to, or the partner itself when it belongs to none.
        """
        for record in self:
            partner = record._agreement_source_partner()
            record.agreement_partner_id = partner.commercial_partner_id or partner

    # Who to reach there - read-only as well, and live for the same reason,
    # since it comes off the same customer.
    agreement_contact_id = fields.Many2one(
        'res.partner', string='Contact Person',
        compute='_compute_agreement_contact')
    # Odoo 19 folded mobile into phone, so there is one number to show.
    agreement_phone = fields.Char(
        string='Phone / Mobile', compute='_compute_agreement_contact_details')
    agreement_email = fields.Char(
        string='Email', compute='_compute_agreement_contact_details')
    agreement_address = fields.Char(
        string='Address', compute='_compute_agreement_contact_details')

    # Every path a customer's details can reach these fields through - and
    # every one of them runs over stored relations only.
    #
    # Depending on agreement_partner_id or agreement_contact_id instead would
    # be the shorter way to say this, but both are computed and unstored:
    # Odoo cannot search them to work out which reports to refresh when a
    # partner's email changes, and says so on every write to a partner.
    # Everything that makes up "how to reach them" - the number, the address
    # and the email - each of which can change on a partner without anything
    # else about the report changing.
    _ADDRESS_LEAVES = ('phone', 'email', 'street', 'street2', 'city', 'zip',
                       'state_id', 'country_id')

    # _ADDRESS_LEAVES comes first on purpose: only the outermost loop of a
    # generator in a class body can see the class's own names.
    _CONTACT_DEPENDS = tuple(
        '%s.partner_id%s.%s' % (root, hop, leaf)
        for leaf in _ADDRESS_LEAVES
        for root in ('agreement_sale_order_id', 'task_id')
        for hop in ('', '.child_ids')
    ) + (
        'agreement_sale_order_id.partner_id',
        'agreement_sale_order_id.partner_id.child_ids',
        'agreement_sale_order_id.partner_id.is_company',
        'task_id.partner_id',
        'task_id.partner_id.child_ids',
        'task_id.partner_id.is_company',
    )

    @api.depends(*_CONTACT_DEPENDS)
    def _compute_agreement_contact_details(self):
        """The chosen contact's number, address and email, beside their name.

        A person inside a company often carries no address of their own, so
        the company's stands in - that is where the engineer is going either
        way.
        """
        for record in self:
            contact = record.agreement_contact_id
            record.agreement_phone = contact.phone
            record.agreement_email = contact.email
            record.agreement_address = (
                record._partner_address(contact)
                or record._partner_address(record.agreement_partner_id))

    def _partner_address(self, partner):
        """One line of address, built from the parts that are filled in.

        Written out here rather than taken from res.partner.contact_address:
        that field is computed and unstored, and depending on one of those is
        what had Odoo warning on every write to a partner.
        """
        if not partner:
            return ''
        parts = [
            partner.street,
            partner.street2,
            partner.city,
            partner.state_id.name,
            partner.zip,
            partner.country_id.name,
        ]
        return ', '.join(part.strip() for part in parts if part and part.strip())

    @api.depends(*_CONTACT_DEPENDS)
    def _compute_agreement_contact(self):
        """The person to reach at the customer.

        Where the contract names a person - on their own, or as a contact
        inside a company - that person is who you call, so they stay here
        while the company goes in the Customer field beside them. A person
        standing alone is simply shown in both.

        Where the contract names a company outright there is no person to
        take, so it stands as its own contact - falling through to the first
        contact beneath it that can actually be reached, since a company
        rarely carries a number of its own.
        """
        for record in self:
            partner = record._agreement_source_partner()
            if partner and not partner.is_company:
                record.agreement_contact_id = partner
                continue

            contact = partner
            if partner and not (partner.phone or partner.email):
                reachable = partner.child_ids.filtered(
                    lambda child: child.phone or child.email)
                contact = reachable[:1] or partner
            record.agreement_contact_id = contact

    # Technical Report - the current task's own data
    task_project_id = fields.Many2one(
        related='task_id.project_id', string='Project', readonly=True)
    task_partner_id = fields.Many2one(
        related='task_id.partner_id', string='Customer', readonly=True)
    task_stage_id = fields.Many2one(
        related='task_id.stage_id', string='Stage', readonly=True)
    task_visit_type = fields.Selection(
        related='task_id.visit_type', string='Visit Type', readonly=True)
    task_date_deadline = fields.Datetime(
        related='task_id.date_deadline', string='Deadline', readonly=True)
    task_user_ids = fields.Many2many(
        related='task_id.user_ids', string='Dispatcher', readonly=True)
    task_pre_dispatch_ids = fields.Many2many(
        related='task_id.pre_dispatch_ids', string='Planned Engineer', readonly=True)
    task_hard_dispatch_id = fields.Many2one(
        related='task_id.hard_dispatch_id', string='Actual Engineer', readonly=True)
    task_description = fields.Html(
        related='task_id.description', string='Description', readonly=True)
    task_create_date = fields.Datetime(
        related='task_id.create_date', string='Task Created On', readonly=True)

    # --- Technical Report -------------------------------------------------
    # The engineer who actually went, straight off the task and not to be
    # edited here. The ID field shows the engineer's own Actual Engineer ID
    # rather than their name - the view passes show_actual_engineer_id for
    # that (see hr_employee.py).
    task_actual_engineer_id_code = fields.Many2one(
        related='task_id.actual_engineer_id_code',
        string='Actual Engineer ID', readonly=True)

    task_no = fields.Integer(
        string='Task No', compute='_compute_task_no',
        help='1 for a task in its own right; a sub-task counts on from its '
             'parent in the order the sub-tasks were added.')

    @api.depends('task_id', 'task_id.parent_id', 'task_id.parent_id.child_ids')
    def _compute_task_no(self):
        """Where this task sits under its parent: the parent itself is 1, its
        first sub-task 2, the next 3, and so on."""
        for record in self:
            task = record.task_id
            parent = task.parent_id
            if not task or not parent:
                record.task_no = 1
                continue
            siblings = parent.child_ids.sorted(key=lambda child: child.id or 0)
            ordinal = (
                list(siblings).index(task) + 1 if task in siblings
                else len(siblings) + 1)
            record.task_no = ordinal + 1

    work_order_no = fields.Char(string='Work Order No')

    # --- Serial Number ----------------------------------------------------
    # One running number per engineer - their name and how many reports they
    # have to their name this year, as Ahmad-000001 - starting again at 1
    # each new year. Only Technical Reports take one: the count is meant to
    # be the engineer's work, not every record the task carries.
    serial_number = fields.Char(
        string='Serial Number (S.N.)', compute='_compute_serial_number',
        store=True, readonly=True, copy=False)
    # What the number was issued against. Kept so a number is never reissued
    # to the same engineer, and so next year's counting knows where to start.
    serial_engineer_id = fields.Many2one(
        'hr.employee', string='S.N. Engineer',
        compute='_compute_serial_number', store=True, readonly=True, copy=False)
    serial_year = fields.Integer(
        string='S.N. Year', compute='_compute_serial_number',
        store=True, readonly=True, copy=False)
    serial_counter = fields.Integer(
        string='S.N. Counter', compute='_compute_serial_number',
        store=True, readonly=True, copy=False)

    @api.depends('report_type', 'task_id.hard_dispatch_id')
    def _compute_serial_number(self):
        """Hand out a number the first time this report has an engineer, and
        again if it changes hands - never otherwise.

        A number already issued is a number somebody has written down, so it
        is only ever kept. Where there is nothing to issue against, what the
        record already holds is written straight back.
        """
        issued_this_batch = {}
        for record in self:
            engineer = record.task_id.hard_dispatch_id
            keep = (
                record.report_type != 'technical_report'
                or not engineer
                or (record.serial_number and record.serial_engineer_id == engineer)
            )
            if keep:
                record.serial_number = record.serial_number
                record.serial_engineer_id = record.serial_engineer_id
                record.serial_year = record.serial_year
                record.serial_counter = record.serial_counter
                continue

            year = fields.Date.context_today(record).year
            key = (engineer.id, year)
            counter = issued_this_batch.get(key)
            if counter is None:
                counter = record._last_serial_counter(engineer, year)
            counter += 1
            issued_this_batch[key] = counter

            record.serial_counter = counter
            record.serial_year = year
            record.serial_engineer_id = engineer
            record.serial_number = '%s-%06d' % ((engineer.name or '').strip(), counter)

    # --- Visits -----------------------------------------------------------
    visit_count = fields.Char(
        string='Visit Count', compute='_compute_visit_count',
        help='Visits of this task\'s type already spent, out of what the '
             'contract allows.')

    @api.depends('task_id.visit_type', 'task_id.project_id', 'task_id.partner_id')
    def _compute_visit_count(self):
        """Spent out of allowed, counted and worded exactly as the task's own
        visit button words it.

        The task owns this arithmetic - which visits count, and how many the
        contract on the Sales Order allows - so it is asked rather than
        repeated here, and the two can never drift apart.
        """
        for record in self:
            task = record.task_id
            if not task:
                record.visit_count = ''
                continue

            allowed, unlimited = task._visit_allowance()
            used = len(task._visit_siblings())

            if unlimited:
                record.visit_count = _('%s / Unlimited', used)
            elif allowed:
                record.visit_count = '%s / %s' % (used, allowed)
            else:
                # nothing to count against - no contract behind the task, or
                # none covering this kind of visit
                record.visit_count = str(used)

    # --- Readings taken on site ------------------------------------------
    # One line per machine under this report's task. Lines are made by
    # _sync_machine_data() below and by nothing else: the Sales Orders say
    # which machines exist, and the form only lets the readings be filled in.
    machine_data_ids = fields.One2many(
        'infinity.machine.data', 'report_id', string='Machine Data')

    def action_print_technical_report(self):
        """Open the printed report.

        The action is looked up here, when the button is pressed, rather than
        named in the view as %(...)d - that form is resolved while the view
        loads, so the report file would have to be loaded first or the whole
        module fails to install.
        """
        self.ensure_one()
        return self.env.ref(
            'infinity.action_report_technical_report').report_action(self)

    def _machine_sources(self):
        """Every machine this report could be about, as (serial, order).

        One Sales Order carries one contract and one machine, so the machines
        under a task are the machines on the confirmed orders for its project
        and customer - the same orders the Agreement may be built from. Two
        orders naming the same machine count once: a machine that was sold
        twice is still one machine to take a reading off.
        """
        self.ensure_one()
        sources = []
        seen = set()
        for order in self._allowed_sale_orders():
            # the contract first, then the order's copy of it: the copy is
            # taken once when the contract is picked, so an order whose
            # contract was picked before the serial was typed kept the blank
            # it was given
            serial = (
                order.service_contract_id.machine_serial_number
                or order.service_contract_machine_serial_number
                or ''
            ).strip()
            if not serial or serial in seen:
                continue
            seen.add(serial)
            sources.append((serial, order))
        return sources

    def _sync_machine_data(self):
        """Make the report carry one line per machine under its task.

        Three machines on the customer's orders for this project, three
        lines; one machine, one line. Lines are added for machines that have
        none, and a line whose machine is no longer among them is cleared
        away - but only while it is still empty. Once an engineer has written
        a reading against a machine, that reading stays, whatever the orders
        are edited to say afterwards.
        """
        for record in self:
            if record.report_type != 'technical_report':
                continue

            sources = record._machine_sources()
            serials = [serial for serial, _order in sources]

            stale = record.machine_data_ids.filtered(
                lambda line: line.machine_serial_number not in serials
                and not line._has_readings())
            if stale:
                stale.unlink()

            known = set(record.machine_data_ids.mapped('machine_serial_number'))
            # only the order is given - the serial is the line's to work
            # out, and nobody's to type
            missing = [
                {'report_id': record.id, 'sale_order_id': order.id}
                for serial, order in sources if serial not in known
            ]
            if missing:
                self.env['infinity.machine.data'].create(missing)

    @api.model_create_multi
    def create(self, vals_list):
        reports = super().create(vals_list)
        reports._sync_machine_data()
        return reports

    def write(self, vals):
        result = super().write(vals)
        # the order changed, so which machines this report is about may have
        if 'agreement_sale_order_id' in vals:
            self._sync_machine_data()
        return result

    # --- Spare parts ------------------------------------------------------
    # What was asked for, and what actually went in - two separate lists,
    # because a part requested is not a part fitted.
    spare_requested_ids = fields.One2many(
        'infinity.technical.report.spare.requested', 'report_id',
        string='Spare Parts Requested')
    spare_installed_ids = fields.One2many(
        'infinity.technical.report.spare.installed', 'report_id',
        string='Spare Parts Installed')

    # --- What was found, and what it took ---------------------------------
    # Html, so a diagnosis can be laid out - a list of what was checked, a
    # line in bold, a table of readings. Odoo's editor grows with what is
    # written into it just as the plain text box did.
    technical_diagnosis = fields.Html(string='Technical Diagnosis')
    work_time_hours = fields.Float(string='Work Time (Hours)')
    travel_time_hours = fields.Float(string='Travel Time (Hours)')

    # --- Signed off -------------------------------------------------------
    fse_signature = fields.Binary(string='FSE Signature', attachment=True)
    customer_signature = fields.Binary(string='Customer Signature', attachment=True)
    customer_comments = fields.Text(string='Customer Comments')

    def _last_serial_counter(self, engineer, year):
        """The highest number this engineer has been given this year.

        Read straight from the table rather than through search(): searching
        from inside a compute makes Odoo flush the very fields being computed,
        and that is a loop back into here.
        """
        self.env.cr.execute(
            """
            SELECT COALESCE(MAX(serial_counter), 0)
            FROM infinity_technical_report
            WHERE serial_engineer_id = %s AND serial_year = %s
            """,
            (engineer.id, year),
        )
        return self.env.cr.fetchone()[0]

    # Visit History - pick an earlier task's Technical Report to review it
    visit_report_id = fields.Many2one(
        'infinity.technical.report', string='Previous Visit')
    visit_task_name = fields.Char(
        related='visit_report_id.task_name', string='Task Name', readonly=True)
    visit_project_id = fields.Many2one(
        related='visit_report_id.task_project_id', string='Project', readonly=True)
    visit_partner_id = fields.Many2one(
        related='visit_report_id.task_partner_id', string='Customer', readonly=True)
    visit_stage_id = fields.Many2one(
        related='visit_report_id.task_stage_id', string='Stage', readonly=True)
    visit_date_deadline = fields.Datetime(
        related='visit_report_id.task_date_deadline', string='Deadline', readonly=True)
    visit_user_ids = fields.Many2many(
        related='visit_report_id.task_user_ids', string='Dispatcher', readonly=True)
    visit_pre_dispatch_ids = fields.Many2many(
        related='visit_report_id.task_pre_dispatch_ids', string='Planned Engineer', readonly=True)
    visit_hard_dispatch_id = fields.Many2one(
        related='visit_report_id.task_hard_dispatch_id', string='Actual Engineer', readonly=True)
    visit_description = fields.Html(
        related='visit_report_id.task_description', string='Description', readonly=True)

    @api.depends('name', 'task_id.name')
    def _compute_display_name(self):
        """Name reports after their task so the picker lists task names."""
        for record in self:
            if record.task_id:
                record.display_name = '%s / %s' % (record.task_id.name, record.name)
            else:
                record.display_name = record.name

    # --- Agreement: the contract terms of the Sales Order that this task's
    # --- project belongs to. Read live (not stored) so the Agreement always
    # --- reflects the order as it stands.

    # --- One customer, or no Agreement ------------------------------------
    # The contract only covers the customer it was signed with, so the task,
    # its project and the Sales Order all have to name the same one. Where
    # they do not, no order is offered and no contract is shown - the
    # customer is the user's to choose, and choosing somebody else's simply
    # means this project's contract does not apply.

    agreement_block_reason = fields.Char(
        string='No Agreement Because', compute='_compute_agreement_block_reason')

    @api.depends('task_id.partner_id', 'task_id.project_id',
                 'task_id.project_id.partner_id')
    def _compute_agreement_block_reason(self):
        for record in self:
            record.agreement_block_reason = record._agreement_block_reason()

    def _agreement_block_reason(self):
        """Why this task's contract cannot be shown, in the user's words -
        or False when nothing stands in the way."""
        self.ensure_one()
        task = self.task_id
        if not task:
            return False
        project = task.project_id
        if not project:
            return _('This task is not on a project, so there is no contract to show.')
        if not task.partner_id:
            return _('This task has no customer, so there is no contract to show.')
        if not project.partner_id:
            return _(
                'The project %(project)s has no customer, so there is nothing '
                'to check this task\'s customer against.',
                project=project.display_name)
        # compared by company: a task for a contact and a project for the
        # company that contact belongs to are the same customer
        if task.partner_id.commercial_partner_id != project.partner_id.commercial_partner_id:
            return _(
                'This task is for %(task_partner)s, but the project %(project)s '
                'is for %(project_partner)s - a contract is only shown when the '
                'task, the project and the Sales Order are all for the same '
                'customer.',
                task_partner=task.partner_id.display_name,
                project=project.display_name,
                project_partner=project.partner_id.display_name)
        return False

    # Found from the task's project to begin with, but left editable so a
    # different order can be picked - everything below follows whichever one
    # is selected.
    agreement_sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order',
        compute='_compute_agreement_sale_order', store=True, readonly=False)

    @api.depends('task_id.project_id', 'task_id.partner_id',
                 'task_id.project_id.partner_id')
    def _compute_agreement_sale_order(self):
        """Fill the order in from the task's project, and keep a hand-picked
        one only while it still belongs to this task.

        The field is computed and editable at once, so every recompute is a
        chance to wipe a deliberate choice - but holding on to one regardless
        is just as wrong: change the task's customer and the Agreement would
        go on showing the previous customer's order.
        """
        for record in self:
            chosen = record.agreement_sale_order_id
            partner = record.task_id.partner_id
            if record._agreement_block_reason():
                record.agreement_sale_order_id = False
            elif chosen and chosen.partner_id.commercial_partner_id == partner.commercial_partner_id:
                record.agreement_sale_order_id = chosen
            else:
                record.agreement_sale_order_id = record._find_sale_order()

    # The orders that may be picked above: confirmed, for this task's project
    # and customer. Worked out here rather than as a domain on the field,
    # because the field linking an order to a project is not always stored
    # and a domain cannot search one that isn't.
    agreement_allowed_order_ids = fields.Many2many(
        'sale.order', string='Selectable Sales Orders',
        compute='_compute_agreement_allowed_orders')

    @api.depends('task_id.project_id', 'task_id.partner_id',
                 'task_id.project_id.partner_id')
    def _compute_agreement_allowed_orders(self):
        for record in self:
            record.agreement_allowed_order_ids = record._allowed_sale_orders()

    def _allowed_sale_orders(self):
        """Confirmed orders for this task's project and customer."""
        self.ensure_one()
        SaleOrder = self.env['sale.order']
        project = self.task_id.project_id
        partner = self.task_id.partner_id
        if self._agreement_block_reason():
            return SaleOrder

        domain = [
            ('state', 'in', ('sale', 'done')),
            # the company and everyone under it - an order raised for a
            # contact belongs to the same customer as one raised for the firm
            ('partner_id', 'child_of', partner.commercial_partner_id.id),
        ]

        # a) search on the link when it is stored
        for field_name in ('project_id', 'project_ids'):
            field = SaleOrder._fields.get(field_name)
            if field is not None and field.store:
                orders = SaleOrder.search(domain + [(field_name, '=', project.id)])
                if orders:
                    return orders

        # b) otherwise read it per order, over the confirmed ones only
        matching = SaleOrder
        for order in SaleOrder.search(domain):
            for field_name in ('project_id', 'project_ids'):
                if field_name in order._fields and project in order[field_name]:
                    matching |= order
                    break
        return matching
    agreement_service_contract_id = fields.Many2one(
        'infinity.service.contract', string='SLA Sub Type', compute='_compute_agreement', readonly=True)
    agreement_full_name = fields.Selection([
        ('warranty', 'Warranty'),
        ('labor_annual_contract', 'Labor Annual Contract'),
        ('service_maintenance_annual_contract', 'Service Maintenance Annual Contract'),
        ('full_service_maintenance_annual_contract', 'Full Service Maintenance Annual Contract'),
        ('cost_per_click', 'Cost Per Click'),
        ('time_material', 'Time & Material'),
    ], string='Full Name', compute='_compute_agreement', readonly=True)
    agreement_abbreviation = fields.Selection([
        ('w', 'W'), ('labor', 'Labor'), ('sma', 'S.M.A'),
        ('fsma', 'F.S.M.A'), ('cpp', 'CPP'), ('tm', 'T&M'),
    ], string='Abbreviation', compute='_compute_agreement', readonly=True)
    agreement_sub_type_value = fields.Char(
        string='SLA Sub Type Value', compute='_compute_agreement', readonly=True)
    agreement_from_date = fields.Date(
        string='From Date', compute='_compute_agreement', readonly=True)
    agreement_to_date = fields.Date(
        string='To Date', compute='_compute_agreement', readonly=True)
    agreement_sla = fields.Float(
        string='SLA', compute='_compute_agreement', readonly=True)
    agreement_sla_unit = fields.Selection([
        ('hours', 'Hours'), ('days', 'Days'),
    ], string='SLA Unit', compute='_compute_agreement', readonly=True)
    agreement_hours = fields.Float(
        string='Hours', compute='_compute_agreement', readonly=True)
    agreement_machine_serial_number = fields.Char(
        string='Machine Serial Number', compute='_compute_agreement', readonly=True)
    agreement_min_number_of_copies = fields.Integer(
        string='Min Number of Copies', compute='_compute_agreement', readonly=True)
    agreement_max_number_of_copies = fields.Integer(
        string='Max Number of Copies', compute='_compute_agreement', readonly=True)
    agreement_volume = fields.Integer(
        string='Volume', compute='_compute_agreement', readonly=True)
    agreement_limited_rv_visits = fields.Integer(
        string='Limited RV Visits', compute='_compute_agreement', readonly=True)
    agreement_limited_pm_visits = fields.Integer(
        string='Limited PM Visits', compute='_compute_agreement', readonly=True)
    agreement_limited_em_visits = fields.Integer(
        string='Limited EM Visits', compute='_compute_agreement', readonly=True)
    agreement_unlimited_em_visits = fields.Boolean(
        string='Unlimited EM Visits', compute='_compute_agreement', readonly=True)
    agreement_spare_parts = fields.Boolean(
        string='Spare Parts', compute='_compute_agreement', readonly=True)
    agreement_pm_parts = fields.Boolean(
        string='PM Parts', compute='_compute_agreement', readonly=True)
    agreement_consumables_including_image_unit = fields.Boolean(
        string='Consumables Including Image Unit', compute='_compute_agreement', readonly=True)
    agreement_consumables_excluding_image_unit = fields.Boolean(
        string='Consumables Excluding Image Unit', compute='_compute_agreement', readonly=True)
    agreement_plain_media = fields.Boolean(
        string='Plain Media', compute='_compute_agreement', readonly=True)
    agreement_pre_printed_media = fields.Boolean(
        string='Pre-Printed Media', compute='_compute_agreement', readonly=True)
    agreement_operators = fields.Boolean(
        string='Operators', compute='_compute_agreement', readonly=True)
    agreement_owned_machines = fields.Boolean(
        string='Owned Machines', compute='_compute_agreement', readonly=True)
    agreement_site = fields.Boolean(
        string='Site', compute='_compute_agreement', readonly=True)
    agreement_machines_rent = fields.Boolean(
        string='Machines Rent', compute='_compute_agreement', readonly=True)

    def _find_sale_order(self):
        """The Sales Order behind this report's task - see
        project.task._infinity_sale_order()."""
        self.ensure_one()
        if not self.task_id:
            return self.env['sale.order']
        return self.task_id._infinity_sale_order()

    @api.depends('agreement_sale_order_id')
    def _compute_agreement(self):
        for record in self:
            order = record.agreement_sale_order_id
            record.agreement_service_contract_id = order.service_contract_id if order else False
            record.agreement_full_name = order.service_contract_full_name if order else False
            record.agreement_abbreviation = order.service_contract_abbreviation if order else False
            record.agreement_sub_type_value = order.service_contract_sub_type_value if order else False
            values = {
                'from_date': order.service_contract_from_date,
                'to_date': order.service_contract_to_date,
                'sla': order.service_contract_sla,
                'sla_unit': order.service_contract_sla_unit,
                'hours': order.service_contract_hours,
                'machine_serial_number': order.service_contract_machine_serial_number,
                'min_number_of_copies': order.service_contract_min_number_of_copies,
                'max_number_of_copies': order.service_contract_max_number_of_copies,
                'volume': order.service_contract_volume,
                'limited_rv_visits': order.service_contract_limited_rv_visits,
                'limited_pm_visits': order.service_contract_limited_pm_visits,
                'limited_em_visits': order.service_contract_limited_em_visits,
                'unlimited_em_visits': order.service_contract_unlimited_em_visits,
                'spare_parts': order.service_contract_spare_parts,
                'pm_parts': order.service_contract_pm_parts,
                'consumables_including_image_unit': order.service_contract_consumables_including_image_unit,
                'consumables_excluding_image_unit': order.service_contract_consumables_excluding_image_unit,
                'plain_media': order.service_contract_plain_media,
                'pre_printed_media': order.service_contract_pre_printed_media,
                'operators': order.service_contract_operators,
                'owned_machines': order.service_contract_owned_machines,
                'site': order.service_contract_site,
                'machines_rent': order.service_contract_machines_rent,
            } if order else {}
            for field_name in ['from_date', 'to_date', 'sla', 'sla_unit', 'hours', 'machine_serial_number', 'min_number_of_copies', 'max_number_of_copies', 'volume', 'limited_rv_visits', 'limited_pm_visits', 'limited_em_visits', 'unlimited_em_visits', 'spare_parts', 'pm_parts', 'consumables_including_image_unit', 'consumables_excluding_image_unit', 'plain_media', 'pre_printed_media', 'operators', 'owned_machines', 'site', 'machines_rent']:
                record['agreement_' + field_name] = values.get(field_name, False)

