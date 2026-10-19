from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Deliveries that are over with are never touched: what went out went out.
_OPEN = ('draft', 'waiting', 'confirmed', 'partially_available', 'assigned')


class StockMove(models.Model):
    _inherit = 'stock.move'

    # True once the machine this move is part of has gone out on any of the
    # transfers the order raised. A delivery in several steps - pick, then
    # quality control, then ship - is one machine leaving, not three, so
    # validating the first step settles the serial for all of them.
    infinity_serial_settled = fields.Boolean(
        string='Serial Settled', compute='_compute_infinity_serial_settled')

    @api.depends('sale_line_id.machine_lot_id', 'sale_line_id.move_ids.state')
    def _compute_infinity_serial_settled(self):
        for move in self:
            line = move.sale_line_id
            move.infinity_serial_settled = bool(
                line and line.machine_lot_id
                and any(other.state == 'done' for other in line.move_ids))

    # Which machine goes out is the order's to say. A move carrying a serial
    # chosen there is closed on the transfer from the start, not only once
    # something has been validated: the two must not be able to disagree.
    infinity_serial_locked = fields.Boolean(
        string='Serial Locked', compute='_compute_infinity_serial_locked')

    @api.depends('sale_line_id.machine_lot_id', 'infinity_serial_settled')
    def _compute_infinity_serial_locked(self):
        for move in self:
            move.infinity_serial_locked = bool(
                move.infinity_serial_settled
                or (move.sale_line_id and move.sale_line_id.machine_lot_id))

    def write(self, vals):
        """Refuse a serial change once the machine has left the building.

        The transfers the order raised are steps of one journey, so the
        first one validated settles which machine this is - and the steps
        still to come cannot be made to say otherwise.

        This module's own writes pass through: they are what puts the sold
        serial here in the first place, and they never touch a settled move.
        """
        if 'lot_ids' in vals and not self.env.context.get('infinity_serial_sync'):
            shut = self.filtered('infinity_serial_locked')
            if shut:
                raise UserError(_(
                    'The serial number of the machine on %(order)s is set on '
                    'the order, not on %(transfer)s. Change it there.',
                    order=shut[0].sale_line_id.order_id.name,
                    transfer=shut[0].picking_id.name or _('this transfer')))
        return super().write(vals)

    def _action_assign(self, *args, **kwargs):
        """Put the serial the order chose onto the delivery.

        Which machine goes to this customer is settled when it is sold, not
        when it is picked. Odoo reserves stock here, so this is the moment
        it has just made its own choice of serial - and the moment to say
        which one was actually sold.
        """
        result = super()._action_assign(*args, **kwargs)
        self._infinity_apply_machine_lot()
        return result

    def _infinity_apply_machine_lot(self):
        """Write the sold serial onto the delivery, over Odoo's own pick.

        The move's own lot_ids is written rather than the lines beneath it:
        that field exists for this, and its inverse moves the reservation
        along with it. Writing on the lines instead leaves the reservation
        pointing at the serial that was let go.

        Only a move for the very product the serial belongs to is touched -
        which for a kit is the component, not the kit - and only while the
        delivery is still open.
        """
        for move in self:
            if move.state not in _OPEN or move.infinity_serial_settled:
                continue
            lot = move.sale_line_id.machine_lot_id if move.sale_line_id else None
            if not lot or lot.product_id != move.product_id:
                continue
            if move.product_id.tracking == 'none':
                continue
            if move.lot_ids == lot:
                continue
            move.with_context(infinity_serial_sync=True).lot_ids = [(6, 0, lot.ids)]

    def _infinity_clear_machine_lot(self, lot):
        """Take a serial back off the delivery when the order lets it go.

        Only the very serial the order was carrying is removed, and only
        from a transfer still open on a machine that has not gone out.
        Whatever else is on the move was put there by stock or by hand, and
        is none of this module's business.
        """
        if not lot:
            return
        for move in self:
            if move.state not in _OPEN or move.infinity_serial_settled:
                continue
            if lot not in move.lot_ids:
                continue
            move.with_context(infinity_serial_sync=True).lot_ids = [(3, lot.id)]


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # The move's answer, carried down so the Detailed Operations list - a
    # view of its own, with no parent to ask - can close its serial fields.
    infinity_serial_settled = fields.Boolean(
        related='move_id.infinity_serial_settled', readonly=True)
    infinity_serial_locked = fields.Boolean(
        related='move_id.infinity_serial_locked', readonly=True)
