from odoo import api, fields, models


class MachineData(models.Model):
    _name = 'infinity.machine.data'
    _description = 'Machine Data'
    _order = 'report_id, id'

    report_id = fields.Many2one(
        'infinity.technical.report', string='Technical Report',
        required=True, ondelete='cascade', index=True)

    # Nobody picks this. The report finds the orders behind its own task and
    # makes a line for each machine on them - see
    # infinity.technical.report._sync_machine_data(). readonly keeps it out
    # of the user's hands, not out of the ORM's.
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', required=True,
        readonly=True, ondelete='cascade')

    # The serial on the contract, falling back to the order's own copy of it.
    # The contract comes first because that is where the number is actually
    # kept up to date: an order's copy is taken once, when its contract is
    # picked, and an order whose contract was picked before the serial was
    # typed keeps the blank it was given.
    machine_serial_number = fields.Char(
        string='Machine Serial Number',
        compute='_compute_machine_serial_number', store=True, index=True)

    @api.depends('sale_order_id.service_contract_id.machine_serial_number',
                 'sale_order_id.service_contract_machine_serial_number')
    def _compute_machine_serial_number(self):
        for line in self:
            order = line.sale_order_id
            line.machine_serial_number = (
                order.service_contract_id.machine_serial_number
                or order.service_contract_machine_serial_number)

    service_contract_id = fields.Many2one(
        related='sale_order_id.service_contract_id',
        string='SLA Sub Type', readonly=True)

    service_counter = fields.Integer(string='Service Counter')
    total_counter = fields.Integer(string='Total Counter')
    color_counter = fields.Integer(string='Color')
    black_counter = fields.Integer(string='Black')

    def _has_readings(self):
        """Has anybody written anything down against this machine yet?"""
        self.ensure_one()
        return bool(self.service_counter or self.total_counter
                    or self.color_counter or self.black_counter)

    @api.depends('machine_serial_number', 'sale_order_id')
    def _compute_display_name(self):
        for line in self:
            line.display_name = (
                line.machine_serial_number or line.sale_order_id.name or '')
