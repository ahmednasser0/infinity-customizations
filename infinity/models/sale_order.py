from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
        'service_contract_unlimited_em_visits': 'unlimited_em_visits',
        'service_contract_spare_parts': 'spare_parts',
        'service_contract_pm_parts': 'pm_parts',
        'service_contract_consumables_including_image_unit': 'consumables_including_image_unit',
        'service_contract_consumables_excluding_image_unit': 'consumables_excluding_image_unit',
        'service_contract_plain_media': 'plain_media',
        'service_contract_pre_printed_media': 'pre_printed_media',
        'service_contract_operators': 'operators',
        'service_contract_owned_machines': 'owned_machines',
        'service_contract_site': 'site',
        'service_contract_machines_rent': 'machines_rent',
    }

    @api.depends('service_contract_id')
    def _compute_from_service_contract(self):
        for order in self:
            contract = order.service_contract_id
            if not contract:
                # Nothing to copy from - and the snapshot already taken is
                # this order's own data, so it stays. A recompute must never
                # be what empties it.
                continue
            for order_field, path in order._CONTRACT_SNAPSHOT.items():
                value = contract
                for step in path.split('.'):
                    value = value[step] if value else False
                order[order_field] = value

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

    # --- This order's own copy, but read-only as requested ---
    service_contract_unlimited_em_visits = fields.Boolean(
        string='Unlimited EM Visits', compute='_compute_from_service_contract', store=True)
    service_contract_spare_parts = fields.Boolean(
        string='Spare Parts', compute='_compute_from_service_contract', store=True)
    service_contract_pm_parts = fields.Boolean(
        string='PM Parts', compute='_compute_from_service_contract', store=True)
    service_contract_consumables_including_image_unit = fields.Boolean(
        string='Consumables Including Image Unit',
        compute='_compute_from_service_contract', store=True)
    service_contract_consumables_excluding_image_unit = fields.Boolean(
        string='Consumables Excluding Image Unit',
        compute='_compute_from_service_contract', store=True)
    service_contract_plain_media = fields.Boolean(
        string='Plain Media', compute='_compute_from_service_contract', store=True)
    service_contract_pre_printed_media = fields.Boolean(
        string='Pre-Printed Media', compute='_compute_from_service_contract', store=True)
    service_contract_operators = fields.Boolean(
        string='Operators', compute='_compute_from_service_contract', store=True)
    service_contract_owned_machines = fields.Boolean(
        string='Owned Machines', compute='_compute_from_service_contract', store=True)
    service_contract_site = fields.Boolean(
        string='Site', compute='_compute_from_service_contract', store=True)
    service_contract_machines_rent = fields.Boolean(
        string='Machines Rent', compute='_compute_from_service_contract', store=True)

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
