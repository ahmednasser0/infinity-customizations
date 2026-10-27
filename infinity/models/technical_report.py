from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TechnicalReport(models.Model):
    _name = 'infinity.technical.report'
    # mail.thread for the chatter at the foot of the form. The spare parts
    # are the reason for it: they stay editable after the report is closed
    # out, so they are the one thing that can change afterwards, and a
    # change nobody can see afterwards is a change nobody can answer for.
    # The lines log themselves - see models/spare_parts.py.
    _inherit = ['mail.thread']
    _description = 'Technical Report'

    name = fields.Char(string='Name', required=True, default='Agreement')
    task_id = fields.Many2one(
        'project.task', string='Task', required=True, ondelete='cascade')
    report_type = fields.Selection([
        ('agreement', 'Agreement'),
        ('technical_report', 'Technical Report'),
    ], string='Report Type', default='agreement')

    # Archiving, so a report can be put away without being destroyed: the
    # visit it describes still happened, and a record of a visit to a
    # customer's machine is not something to throw out because a screen got
    # untidy. Deleting is available too - see the views - for the ones that
    # should never have existed.
    #
    # Anything that looks up a task's reports has to ignore this field, or
    # archiving one would read as the task having none and a second would be
    # made in its place. project_task.py does that lookup, with
    # active_test=False.
    active = fields.Boolean(string='Active', default=True)

    task_name = fields.Char(related='task_id.name', string='Task Name', readonly=True)

    # The customer this agreement is with: the one the selected Sales Order
    # was raised for, falling back to the task's own where no order is
    # picked yet.
    #
    # Worked out on every read rather than stored: a stored value only ever
    # changes when Odoo decides to recompute it, which is how the Agreement
    # ended up holding a customer that had since been changed elsewhere -
    # and how a single empty recompute could leave the field blank for good.
    # 'Customer Name' rather than 'Customer': task_partner_id is the
    # Customer, and two fields of one model sharing a label is what Odoo
    # warns about - a search list offered 'Customer' twice with no way to
    # tell them apart. The search view already called this one Customer
    # Name, and so does the printed report, so the name it answers to is now
    # the name it was already going by.
    agreement_partner_id = fields.Many2one(
        'res.partner', string='Customer Name',
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

    # Whoever went along with them.
    task_fse_accompany_ids = fields.Many2many(
        related='task_id.fse_accompany_ids',
        string='FSE Accompany', readonly=True)

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

    # When the visit happened. The task's creation date is the day the task
    # was drawn up, which is not the same day, so the report carries a date of
    # its own for the engineer to set.
    report_date = fields.Date(
        string='Date', default=fields.Date.context_today)

    # The day this visit counts as having happened. The engineer's own date
    # where there is one, and the day the task was raised otherwise - which
    # is what reports written before that field existed have to fall back
    # on. Stored because the visit history searches and sorts on it.
    visit_date = fields.Date(
        string='Visit Date', compute='_compute_visit_date', store=True)

    @api.depends('report_date', 'task_id.create_date')
    def _compute_visit_date(self):
        for record in self:
            created = record.task_id.create_date
            record.visit_date = (
                record.report_date or (created and created.date()) or False)

    # Typed on the task, read here: one visit, one order number, wherever it
    # is looked at.
    work_order_no = fields.Char(
        related='task_id.work_order_no', string='Work Order No', readonly=True)

    # How the visit ended. Two states, so one field rather than two boxes
    # that could both be ticked at once.
    task_status = fields.Selection([
        ('done', 'Done'),
        ('in_complete', 'In Complete'),
    ], string='Task Status')

    # --- When the visit began, and when it was closed out ------------------
    # Both are stamped by code and never typed. readonly is set here as well
    # as on the form on purpose: the attribute on the view only stops the
    # box on screen, this stops anything else that would write a time by
    # hand. A time somebody can edit is not a measurement, it is a claim.
    visit_start = fields.Datetime(string='Visit Start', readonly=True, copy=False)
    visit_end = fields.Datetime(string='Visit End', readonly=True, copy=False)

    # What the form reads to grey itself out. A plain stored boolean, not a
    # computed one, and that is the whole point: a computed field would be
    # worked out again in the browser the instant somebody picked a status,
    # so the counters and the diagnosis would grey out underneath an
    # engineer who had not written them yet. This one is only ever set on
    # the way through write(), so the form locks when the report is saved
    # with a status - not while it is still being filled in.
    visit_closed = fields.Boolean(string='Closed Out', readonly=True, copy=False)

    def write(self, vals):
        """Close the visit out the first time a Task Status is given.

        "As soon as I put a value in Task Status" - so the stamp is the
        moment the visit was first closed out, with whichever of the two
        answers it was closed out with. Correcting Done to In Complete an
        hour later does not move it: the visit did not end twice. Clearing
        the status does not clear it either, for the same reason.
        """
        if not vals.get('task_status'):
            return super().write(vals)

        unstamped = self.filtered(lambda report: not report.visit_end)
        result = super().write(vals)
        if unstamped:
            super(TechnicalReport, unstamped).write({
                'visit_end': fields.Datetime.now(),
            })
        # Set every time rather than only for the unstamped: a report closed
        # out before this field existed has a status and no flag, and the
        # first save after the upgrade should settle that too.
        super(TechnicalReport, self.filtered(
            lambda report: not report.visit_closed)).write({'visit_closed': True})
        return result

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

    @api.depends('report_type', 'task_id.hard_dispatch_id', 'report_date')
    def _compute_serial_number(self):
        """Hand out a number the first time this report has an engineer, and
        again if it changes hands or the year moves - never otherwise.

        The year is the report's own date, not today's: a report written up
        for last December belongs to last December's count, and moving a
        report into a new year starts it at 1 there while carrying on from
        where that year's count had got to.

        A number already issued for the right engineer in the right year is
        a number somebody has written down, so it is kept. Where there is
        nothing to issue against, what the record already holds is written
        straight back.
        """
        issued_this_batch = {}
        for record in self:
            engineer = record.task_id.hard_dispatch_id
            year = (record.report_date
                    or fields.Date.context_today(record)).year
            keep = (
                record.report_type != 'technical_report'
                or not engineer
                or (record.serial_number
                    and record.serial_engineer_id == engineer
                    and record.serial_year == year)
            )
            if keep:
                record.serial_number = record.serial_number
                record.serial_engineer_id = record.serial_engineer_id
                record.serial_year = record.serial_year
                record.serial_counter = record.serial_counter
                continue

            key = (engineer.id, year)
            counter = issued_this_batch.get(key)
            if counter is None:
                counter = record._last_serial_counter(engineer, year)
            counter += 1
            issued_this_batch[key] = counter

            record.serial_counter = counter
            record.serial_year = year
            record.serial_engineer_id = engineer
            record.serial_number = '%s-%s-%06d' % (
                (engineer.name or '').strip(), year, counter)

    # --- Visits -----------------------------------------------------------
    visit_over_display = fields.Char(
        related='task_id.visit_over_display',
        string='Visits Over the Allowance', readonly=True)
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

    # --- The machine, and what it read -----------------------------------
    # The serial is found, not typed: the orders behind this report's task
    # name the machine, and the contract on the order is where that number is
    # kept up to date. The rest is what the engineer standing in front of it
    # writes down.
    machine_serial_number = fields.Char(
        string='Printing Serial Number',
        compute='_compute_machine_serial_number', store=True,
        readonly=True, index=True)
    # Offered, not dictated. The contract's IT serial is put here when the
    # report is opened and there is nothing in it yet, and from then on it
    # belongs to the engineer standing in front of the machine - they can
    # read the sticker, and the contract may never have been told it.
    #
    # Deliberately not a computed field, which is how the printing serial
    # does it. A stored compute that left a typed value alone would have to
    # read the field inside its own compute method to know there was one,
    # and Odoo recomputes by marking the field unknown first - so that read
    # is a recursion, not an answer. Filling it in from outside the compute
    # has no such problem.
    it_serial_number = fields.Char(string='IT Serial Number', index=True)

    # The order's own serial has to be watched, not just which order it is:
    # the number is filled in later, when the machine goes out on a
    # delivery, and a report that only watched the link would keep the blank
    # it was created with.
    @api.depends('agreement_sale_order_id',
                 'agreement_sale_order_id.service_contract_machine_serial_number',
                 'agreement_sale_order_id.service_contract_id.machine_serial_number',
                 'task_id', 'task_id.project_id', 'task_id.partner_id')
    def _compute_machine_serial_number(self):
        for record in self:
            record.machine_serial_number = record._machine_serial() or False

    def _infinity_fill_it_serial(self):
        """Put the contract's IT serial on reports that have none.

        Only the empty ones: a number somebody typed is the number somebody
        read off the machine, and the contract is the less reliable of the
        two about a sticker.
        """
        for record in self.filtered(lambda report: not report.it_serial_number):
            serial = record._it_serial()
            if serial:
                record.it_serial_number = serial

    # Read off the product the machine is, not typed on the report. One
    # machine model is one machine model however many visits it has had, so
    # it is answered once on the product and read everywhere else.
    #
    # Not stored: a stored compute would write over whatever was typed into
    # these before today, and what was typed is somebody's work. Unstored,
    # the old columns simply stop being read - the words are still in the
    # database if they are ever wanted back.
    machine_model = fields.Char(
        string='Machine Model', compute='_compute_machine_details')
    manufacturer = fields.Char(
        string='Manufacturer', compute='_compute_machine_details')

    def _machine_product(self):
        """The product the machine on this report is."""
        self.ensure_one()
        order = self._find_sale_order()
        if not order:
            return self.env['product.product']
        return order.machine_lot_id.product_id

    @api.depends('task_id', 'agreement_sale_order_id', 'machine_serial_number')
    def _compute_machine_details(self):
        for record in self:
            product = record._machine_product()
            record.machine_model = product.infinity_machine_model or False
            record.manufacturer = product.infinity_manufacturer or False

    # All four are read off a meter that does not always land on a whole
    # number, so they are kept to two places rather than rounded on entry.
    service_counter = fields.Float(string='Service Counter', digits=(16, 2))
    total_counter = fields.Float(string='Total Counter', digits=(16, 2))
    color_counter = fields.Float(string='Color', digits=(16, 2))
    black_counter = fields.Float(string='Black', digits=(16, 2))

    def action_print_technical_report(self):
        """Open the printed report.

        The action is looked up here, when the button is pressed, rather than
        named in the view as %(...)d - that form is resolved while the view
        loads, so the report file would have to be loaded first or the whole
        module fails to install.
        """
        self.ensure_one()
        # The button that calls this is hidden until there is a Task Status,
        # so in ordinary use this never fires. It is here for the ways in
        # that a hidden button does not cover - a call from elsewhere, or a
        # binding still sitting in a database that has not had this version
        # yet. "Print only once the visit has an outcome" is meant to be
        # true of the report, not just of one button.
        if not self.task_status:
            raise UserError(_(
                'This Technical Report has no Task Status yet. Say whether '
                'the visit was Done or In Complete, and it can be printed.'))
        # printed from a list the report was never opened from, so the
        # serial is worked out again here too
        self._compute_machine_serial_number()
        return self.env.ref(
            'infinity.action_report_technical_report').report_action(self)

    # --- The parts asked for, turned into a quotation ---------------------
    # Remembered so a second press opens what the first press made, rather
    # than quoting the same parts over again. Somebody pressing twice means
    # "did that work?", not "do it twice".
    sale_quotation_id = fields.Many2one(
        'sale.order', string='Quotation', readonly=True, copy=False)

    def action_set_to_quotation(self):
        """Quote the Spare Parts Requested, for this customer and project.

        Nothing is quoted where nothing was asked for: the button is left to
        do nothing rather than complain, which is what was asked for.
        """
        self.ensure_one()

        # A quotation that is still a quotation is the one this report made,
        # so it is opened rather than duplicated. One that has been
        # confirmed is no longer open to having parts dropped into it - the
        # customer has agreed to what was on it - so the parts added since
        # are quoted afresh.
        if self.sale_quotation_id and self._quotation_is_open():
            return self._open_quotation()

        lines = self.spare_requested_ids.filtered('product_id')
        if not lines:
            return False

        partner = self.task_partner_id or self.agreement_partner_id
        if not partner:
            return False

        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            # sale_project's own field. Its view limits the choice to
            # billable projects, but that is a domain on a dropdown, not a
            # constraint - written from here any project is accepted, and
            # since 0.60 every project is billable anyway.
            'project_id': self.task_project_id.id or False,
            'origin': self.serial_number or self.task_name or '',
            'order_line': [
                (0, 0, {
                    'product_id': line.product_id.id,
                    # The quantity as the engineer wrote it, including a
                    # zero. A quantity nobody asked for is not a detail to
                    # invent on their behalf.
                    'product_uom_qty': line.qty,
                })
                for line in lines
            ],
        })
        self.sale_quotation_id = order
        return self._open_quotation()

    def _quotation_is_open(self):
        """Whether this report's quotation is still a quotation.

        Draft and Sent are a quotation. Confirmed is an order somebody has
        agreed to, and Cancelled is nothing at all - neither takes a part
        added afterwards.
        """
        self.ensure_one()
        return self.sale_quotation_id.state in ('draft', 'sent')

    def _infinity_quote_lines(self, lines):
        """Put these requested parts on this report's open quotation.

        Called when a part is added to a report that already has one, so
        the quotation keeps up with the report instead of being a snapshot
        of the moment the button was pressed. Nothing happens where there
        is no quotation, or where it has been confirmed: see above.
        """
        self.ensure_one()
        if not (self.sale_quotation_id and self._quotation_is_open()):
            return
        lines = lines.filtered('product_id')
        if not lines:
            return
        self.sale_quotation_id.write({
            'order_line': [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                })
                for line in lines
            ],
        })

    def _open_quotation(self):
        """The quotation this report made, on its own form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.sale_quotation_id.display_name,
            'res_model': 'sale.order',
            'res_id': self.sale_quotation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _machine_serial(self):
        """The serial of the machine this report is about.

        One Sales Order carries one contract and one machine, so the machine
        under a task is the machine on the order behind it - the order the
        Agreement is built from where there is one, otherwise the first of
        the orders this report is allowed to read.

        The order's own number is asked before the contract's. It is the
        order that says which machine this customer was actually sent: it
        is filled in from the serial chosen on the line and corrected again
        when the goods go out. The contract's number is typed by hand, and
        where the two disagree it is the one that has gone stale - so it
        only stands in when the order has nothing to say.
        """
        self.ensure_one()
        orders = (
            self.agreement_sale_order_id
            or self._allowed_sale_orders()
            # the strict rule above wants task, project and order to name one
            # customer; where they do not, the task's own lookup still finds
            # the order its project was sold under
            or self.task_id._infinity_sale_order()
        )
        for order in orders:
            serial = (
                order.service_contract_machine_serial_number
                or order.service_contract_id.machine_serial_number
                or ''
            ).strip()
            if serial:
                return serial
        return ''

    def _it_serial(self):
        """The IT serial of the same machine, found the same way.

        Asked in the same order as the printing serial and over the same
        orders, so a report cannot end up carrying two numbers that belong
        to two different machines.
        """
        self.ensure_one()
        orders = (
            self.agreement_sale_order_id
            or self._allowed_sale_orders()
            or self.task_id._infinity_sale_order()
        )
        for order in orders:
            serial = (
                order.service_contract_it_serial_number
                or order.service_contract_id.it_serial_number
                or ''
            ).strip()
            if serial:
                return serial
        return ''

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
    # The contract's own copy, which since 0.59 is no longer the one that
    # decides: machine_serial_number asks the order first. Named apart from
    # it so a search list does not offer 'Machine Serial Number' twice; the
    # Agreement form still shows it under the short name, where it is the
    # only serial on screen.
    agreement_machine_serial_number = fields.Char(
        string='Contract Printing Serial Number',
        compute='_compute_agreement', readonly=True)
    # Named apart from it_serial_number for the same reason
    # agreement_machine_serial_number is: two fields of one model sharing a
    # label is what Odoo warns about, and a search list offering 'IT Serial
    # Number' twice tells nobody which is which. The Agreement form shows it
    # under the short name, where it is the only one on screen.
    agreement_it_serial_number = fields.Char(
        string='Contract IT Serial Number',
        compute='_compute_agreement', readonly=True)
    agreement_paper_size = fields.Selection([
        ('a3', 'A3'), ('a4', 'A4'),
    ], string='Paper Size', compute='_compute_agreement', readonly=True)
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

    # Every agreement_X on this model is the order's service_contract_X,
    # named once. It used to be named twice - a dict of values and a list of
    # field names to copy them into - and the two drifted the moment a field
    # was added to one of them: the compute then left agreement_X unassigned
    # and Odoo refused to read the record at all. Naming them once is what
    # stops that happening again.
    _AGREEMENT_SNAPSHOT = (
        'from_date',
        'to_date',
        'sla',
        'sla_unit',
        'hours',
        'machine_serial_number',
        'it_serial_number',
        'paper_size',
        'min_number_of_copies',
        'max_number_of_copies',
        'volume',
        'limited_rv_visits',
        'limited_pm_visits',
        'limited_em_visits',
        'unlimited_em_visits',
        'spare_parts',
        'pm_parts',
        'consumables_including_image_unit',
        'consumables_excluding_image_unit',
        'plain_media',
        'pre_printed_media',
        'operators',
        'owned_machines',
        'site',
        'machines_rent',
    )

    @api.depends('agreement_sale_order_id')
    def _compute_agreement(self):
        for record in self:
            order = record.agreement_sale_order_id
            record.agreement_service_contract_id = order.service_contract_id if order else False
            record.agreement_full_name = order.service_contract_full_name if order else False
            record.agreement_abbreviation = order.service_contract_abbreviation if order else False
            record.agreement_sub_type_value = order.service_contract_sub_type_value if order else False
            for field_name in record._AGREEMENT_SNAPSHOT:
                record['agreement_' + field_name] = (
                    order['service_contract_' + field_name] if order else False)

