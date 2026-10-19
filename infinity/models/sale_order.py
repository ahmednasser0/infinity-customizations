from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Lists Service Contracts by their Contract Type's SLA Sub Type.
    service_contract_id = fields.Many2one(
        'infinity.service.contract',
        string='SLA Sub Type',
    )

    # The whole Service Contract, copied onto this order. These are NOT
    # related fields: picking a contract above fills them in once, and from
    # then on they belong to this order alone - editing them here never
    # touches the contract, nor any other order pointing at it. Picking a
    # different contract refills them from that one.
    #
    # That is what compute + store=True + readonly=False buys: the compute
    # acts as a fill-in whenever service_contract_id changes, and the value
    # stays editable in between. The checkboxes leave readonly=False off, so
    # they are filled the same way but cannot be edited by hand.

    # Snapshot source: sale.order field -> path from the Service Contract.
    _CONTRACT_SNAPSHOT = {
        'service_contract_machine_serial_number': 'machine_serial_number',
        'service_contract_from_date': 'from_date',
        'service_contract_to_date': 'to_date',
        'service_contract_sla': 'sla',
        'service_contract_sla_unit': 'sla_unit',
        'service_contract_min_number_of_copies': 'min_number_of_copies',
        'service_contract_max_number_of_copies': 'max_number_of_copies',
        'service_contract_volume': 'volume',
        'service_contract_limited_rv_visits': 'limited_rv_visits',
        'service_contract_limited_pm_visits': 'limited_pm_visits',
        'service_contract_limited_em_visits': 'limited_em_visits',
        'service_contract_hours': 'hours',
    }

    @api.depends('service_contract_id', 'order_line.product_id',
                 'machine_lot_id')
    def _compute_from_service_contract(self):
        for order in self:
            contract = order.service_contract_id
            if contract:
                for order_field, path in order._CONTRACT_SNAPSHOT.items():
                    value = contract
                    for step in path.split('.'):
                        value = value[step] if value else False
                    order[order_field] = value
            # Nothing to copy from leaves the snapshot alone: what was taken
            # is this order's own data, and a recompute must never be what
            # empties it.

            # The machine's own serial beats the contract's copy of it: the
            # contract is typed by hand, this is read off the thing sold.
            serial = order._engine_serial_number()
            if serial:
                order.service_contract_machine_serial_number = serial

    # --- The machine that was sold ---------------------------------------
    # Which serial went out is chosen on the line that sells the machine,
    # beside the product it belongs to. The order only reports it: with one
    # machine to an order there is one serial to report, and it is the first
    # line that names one.
    machine_lot_id = fields.Many2one(
        'stock.lot', string='Machine Serial Number',
        compute='_compute_machine_lot_id', store=True, readonly=True)

    @api.depends('order_line.machine_lot_id')
    def _compute_machine_lot_id(self):
        for order in self:
            chosen = order.order_line.mapped('machine_lot_id')
            order.machine_lot_id = chosen[:1]

    def _engine_serial_number(self):
        """The serial of the machine on this order, as the lines have it."""
        self.ensure_one()
        return self.machine_lot_id.name or ''

    # --- Contract Type identity ------------------------------------------
    # These name the contract type rather than set this order's terms, so
    # there is nothing here to keep a copy of: they are read straight off
    # the chosen contract on every read. Stored, they were only ever a
    # chance to hold nothing - which is exactly what they came to hold.
    service_contract_full_name = fields.Selection(
        related='service_contract_id.contract_type_abbreviation',
        string='Full Name', readonly=True)
    service_contract_abbreviation = fields.Selection(
        related='service_contract_id.contract_type_name',
        string='Abbreviation', readonly=True)
    service_contract_sub_type_value = fields.Char(
        related='service_contract_id.contract_type_sla_sub_type',
        string='SLA Sub Type Value', readonly=True)

    # --- This order's own copy of the contract terms (editable) ---
    service_contract_machine_serial_number = fields.Char(
        string='Machine Serial Number',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_from_date = fields.Date(
        string='From Date',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_to_date = fields.Date(
        string='To Date',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_sla = fields.Float(
        string='SLA',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_sla_unit = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
    ], string='SLA Unit',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_min_number_of_copies = fields.Integer(
        string='Min Number of Copies',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_max_number_of_copies = fields.Integer(
        string='Max Number of Copies',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_volume = fields.Integer(
        string='Volume',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_limited_rv_visits = fields.Integer(
        string='Limited RV Visits',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_limited_pm_visits = fields.Integer(
        string='Limited PM Visits',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_limited_em_visits = fields.Integer(
        string='Limited EM Visits',
        compute='_compute_from_service_contract', store=True, readonly=False)
    service_contract_hours = fields.Float(
        string='Hours',
        compute='_compute_from_service_contract', store=True, readonly=False)

    # --- What the contract includes -------------------------------------
    # Read straight off the contract, not copied onto the order. Nobody edits
    # these here, so a copy has nothing to protect - and a copy is taken once,
    # when the contract is picked, which is how an order came to sit on eleven
    # blank boxes and the Agreement behind it had nothing to show.
    service_contract_unlimited_em_visits = fields.Boolean(
        related='service_contract_id.unlimited_em_visits',
        string='Unlimited EM Visits', readonly=True)
    service_contract_spare_parts = fields.Boolean(
        related='service_contract_id.spare_parts',
        string='Spare Parts', readonly=True)
    service_contract_pm_parts = fields.Boolean(
        related='service_contract_id.pm_parts',
        string='PM Parts', readonly=True)
    service_contract_consumables_including_image_unit = fields.Boolean(
        related='service_contract_id.consumables_including_image_unit',
        string='Consumables Including Image Unit', readonly=True)
    service_contract_consumables_excluding_image_unit = fields.Boolean(
        related='service_contract_id.consumables_excluding_image_unit',
        string='Consumables Excluding Image Unit', readonly=True)
    service_contract_plain_media = fields.Boolean(
        related='service_contract_id.plain_media',
        string='Plain Media', readonly=True)
    service_contract_pre_printed_media = fields.Boolean(
        related='service_contract_id.pre_printed_media',
        string='Pre-Printed Media', readonly=True)
    service_contract_operators = fields.Boolean(
        related='service_contract_id.operators',
        string='Operators', readonly=True)
    service_contract_owned_machines = fields.Boolean(
        related='service_contract_id.owned_machines',
        string='Owned Machines', readonly=True)
    service_contract_site = fields.Boolean(
        related='service_contract_id.site',
        string='Site', readonly=True)
    service_contract_machines_rent = fields.Boolean(
        related='service_contract_id.machines_rent',
        string='Machines Rent', readonly=True)

    @api.constrains('service_contract_from_date', 'service_contract_to_date')
    def _check_service_contract_dates(self):
        for order in self:
            start, end = order.service_contract_from_date, order.service_contract_to_date
            if start and end and start > end:
                raise ValidationError(_(
                    'From Date (%(from_date)s) must come before To Date (%(to_date)s).',
                    from_date=start,
                    to_date=end,
                ))

    @api.constrains('service_contract_min_number_of_copies',
                    'service_contract_max_number_of_copies')
    def _check_service_contract_number_of_copies(self):
        for order in self:
            minimum = order.service_contract_min_number_of_copies
            maximum = order.service_contract_max_number_of_copies
            if minimum > maximum:
                raise ValidationError(_(
                    'Min Number of Copies (%(minimum)s) cannot be greater than '
                    'Max Number of Copies (%(maximum)s).',
                    minimum=minimum,
                    maximum=maximum,
                ))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # The machine this line sells, where it sells one. A kit resolves to the
    # component ticked Engine on its Bill of Materials; anything else is the
    # machine itself. It is what the serial below has to be a serial of, and
    # what keeps the list of serials to that machine's own.
    engine_product_id = fields.Many2one(
        'product.product', string='Machine',
        compute='_compute_engine_product_id', store=True, readonly=True)

    @api.depends('product_id')
    def _compute_engine_product_id(self):
        for line in self:
            line.engine_product_id = line._infinity_engine_product()

    # Which one of that machine went out. One serial to the product's name
    # needs no asking and is filled in; several and the choice is the
    # seller's, which is what this is for.
    machine_lot_id = fields.Many2one(
        'stock.lot', string='Machine Serial Number',
        domain="[('product_id', '=', engine_product_id)]",
        compute='_compute_machine_lot_id', store=True, readonly=False)

    # Once the machine has gone out, its serial is a matter of record.
    # Nothing here may change it, and the field is closed on the form.
    machine_lot_locked = fields.Boolean(
        string='Machine Delivered', compute='_compute_machine_lot_locked')

    @api.depends('move_ids.state')
    def _compute_machine_lot_locked(self):
        for line in self:
            line.machine_lot_locked = any(
                move.state == 'done' for move in line.move_ids)

    @api.depends('engine_product_id')
    def _compute_machine_lot_id(self):
        for line in self:
            if line.machine_lot_locked:
                continue
            product = line.engine_product_id
            if not product:
                line.machine_lot_id = False
                continue
            # a choice already made for this machine is left alone
            if line.machine_lot_id.product_id == product:
                continue
            free = line._infinity_free_lots(product)
            line.machine_lot_id = free if len(free) == 1 else False

    def _infinity_free_lots(self, product, limit=2):
        """That machine's serials that are nobody else's.

        The same two rules the check below applies: a serial promised on
        another order and not yet gone is spoken for, and one that was
        delivered and never came back is gone for good. What is left - never
        sold, or sold and returned - is free to fill in here.
        """
        taken = self.search([
            ('machine_lot_id.product_id', '=', product.id),
            ('state', '!=', 'cancel'),
            ('id', '!=', self._origin.id or 0),
        ])
        promised = taken.filtered(
            lambda other: not other.machine_lot_locked).machine_lot_id
        gone = (taken.machine_lot_id - promised).filtered(
            lambda lot: not self._infinity_lot_on_hand(lot))
        return self.env['stock.lot'].search([
            ('product_id', '=', product.id),
            ('id', 'not in', (promised | gone).ids),
        ], limit=limit)

    def write(self, vals):
        """A serial changed after the order was confirmed goes straight out
        to the delivery, rather than waiting for stock to be reserved again.

        Changing it on a confirmed order is changing which machine this
        customer is to be sent, and the picker is the one who needs to know.
        Clearing it says no machine is promised yet, so the one that was
        promised comes back off the delivery.
        """
        if 'machine_lot_id' in vals:
            wanted = vals['machine_lot_id'] or False
            shut = self.filtered(
                lambda line: line.machine_lot_locked
                and (line.machine_lot_id.id or False) != wanted)
            if shut:
                raise UserError(_(
                    'The machine on %(order)s has already been delivered. '
                    'Its serial number cannot be changed.',
                    order=shut[0].order_id.name))

        letting_go = {
            line.id: line.machine_lot_id for line in self
        } if 'machine_lot_id' in vals else {}

        result = super().write(vals)

        for line in self if letting_go else self.browse():
            if line.machine_lot_id:
                line.move_ids._infinity_apply_machine_lot()
            else:
                line.move_ids._infinity_clear_machine_lot(
                    letting_go.get(line.id))
        return result

    @api.constrains('machine_lot_id')
    def _check_machine_lot_used_once(self):
        """A machine is in one place at a time, and is sold from where it is.

        What is refused is the serial being used again while that machine is
        somebody else's, not the product being sold again: the same product
        can be sold as often as there are machines of it, each under its own
        number.

        Two ways a serial comes free. A cancelled order never sent the
        machine anywhere. And a machine that went out and came back - a
        return - is in the warehouse again, so it can be sold again; being
        back in stock is what says so, not what the old order still reads.
        """
        for line in self:
            lot = line.machine_lot_id
            if not lot:
                continue
            others = self.search([
                ('machine_lot_id', '=', lot.id),
                ('id', '!=', line.id),
                ('state', '!=', 'cancel'),
            ])
            if not others:
                continue

            # still promised to somebody and not yet gone: that machine is
            # spoken for, whatever the warehouse says
            promised = others.filtered(lambda other: not other.machine_lot_locked)
            if promised:
                raise ValidationError(_(
                    'Serial number "%(serial)s" is already promised on '
                    '%(order)s. Pick another serial number for this '
                    'machine.',
                    serial=lot.name,
                    order=promised[0].order_id.name))

            # every other order has had it delivered - so this is only
            # allowed if the machine has since come back to us
            if not line._infinity_lot_on_hand(lot):
                raise ValidationError(_(
                    'Serial number "%(serial)s" was delivered on %(order)s '
                    'and has not come back. Pick another serial number for '
                    'this machine.',
                    serial=lot.name,
                    order=others[0].order_id.name))

    def _infinity_lot_on_hand(self, lot):
        """Is that machine in our own warehouse right now?

        Counted off the quants in internal locations: a machine sitting at a
        customer is in a customer location and does not count, and one that
        came back on a return is in stock again and does.
        """
        quants = lot.quant_ids.filtered(
            lambda quant: quant.location_id.usage == 'internal')
        return sum(quants.mapped('quantity')) > 0

    def _infinity_engine_product(self):
        """The product on this line that carries the machine's serial.

        A kit resolves to whichever of its components is ticked Engine; a kit
        with none ticked names no machine at all, rather than the first
        component or the kit itself. Anything that is not a kit is the
        machine itself.
        """
        self.ensure_one()
        product = self.product_id
        if not product:
            return self.env['product.product']

        Bom = self.env.get('mrp.bom')
        if Bom is None:
            return product

        found = Bom._bom_find(product, company_id=self.company_id.id,
                              bom_type='phantom')
        bom = found.get(product)
        if not bom:
            return product
        return bom.bom_line_ids.filtered('engine')[:1].product_id
