from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Everything a user actually fills in on a contract. Two contracts matching
# on all of it are the same contract entered twice - see _check_duplicate.
CONTRACT_FIELDS = [
    'name',
    'machine_serial_number',
    'from_date',
    'to_date',
    'sla',
    'sla_unit',
    'min_number_of_copies',
    'max_number_of_copies',
    'volume',
    'limited_rv_visits',
    'unlimited_em_visits',
    'spare_parts',
    'limited_pm_visits',
    'limited_em_visits',
    'hours',
    'pm_parts',
    'consumables_excluding_image_unit',
    'consumables_including_image_unit',
    'plain_media',
    'pre_printed_media',
    'operators',
    'owned_machines',
    'machines_rent',
    'site',
]


class ServiceContract(models.Model):
    _name = 'infinity.service.contract'
    _description = 'Service Contract'

    machine_serial_number = fields.Char(string='Machine Serial Number')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    sla = fields.Float(string='SLA')
    sla_unit = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
    ], string='SLA Unit', default='hours')
    min_number_of_copies = fields.Integer(string='Min Number of Copies')
    max_number_of_copies = fields.Integer(string='Max Number of Copies')
    volume = fields.Integer(string='Volume')

    # Lists Contract Types by their SLA Sub Type (see the Contract Type
    # model's _compute_display_name).
    name = fields.Many2one('infinity.contract.type', string='SLA Sub Type', required=True)

    # Pulled read-only from the linked Contract Type: the first two are shown
    # under it on the form, the last one only drives field visibility below.
    contract_type_abbreviation = fields.Selection(
        related='name.abbreviation', string='Full Name', readonly=True)
    contract_type_name = fields.Selection(
        related='name.name', string='Abbreviation', readonly=True)
    contract_type_sla_sub_type = fields.Char(related='name.sub_type_value', string='SLA Sub Type Value')

    # Moved here from Contract Type (independent fields, not related).
    limited_rv_visits = fields.Integer(string='Limited RV Visits', default=12)
    unlimited_em_visits = fields.Boolean(string='Unlimited EM Visits', default=True)
    spare_parts = fields.Boolean(string='Spare Parts', default=True)
    limited_pm_visits = fields.Integer(string='Limited PM Visits', default=12)
    limited_em_visits = fields.Integer(string='Limited EM Visits', default=12)
    hours = fields.Float(string='Hours', default=12)
    pm_parts = fields.Boolean(string='PM Parts', default=True)
    consumables_excluding_image_unit = fields.Boolean(string='Consumables Excluding Image Unit', default=True)
    consumables_including_image_unit = fields.Boolean(string='Consumables Including Image Unit', default=True)
    plain_media = fields.Boolean(string='Plain Media', default=True)
    pre_printed_media = fields.Boolean(string='Pre-Printed Media', default=True)
    operators = fields.Boolean(string='Operators', default=True)
    owned_machines = fields.Boolean(string='Owned Machines', default=True)
    machines_rent = fields.Boolean(string='Machines Rent', default=True)
    site = fields.Boolean(string='Site', default=True)

    @api.constrains('from_date', 'to_date')
    def _check_dates(self):
        for contract in self:
            if contract.from_date and contract.to_date and contract.from_date > contract.to_date:
                raise ValidationError(_(
                    'From Date (%(from_date)s) must come before To Date (%(to_date)s).',
                    from_date=contract.from_date,
                    to_date=contract.to_date,
                ))

    @api.constrains('min_number_of_copies', 'max_number_of_copies')
    def _check_number_of_copies(self):
        for contract in self:
            if contract.min_number_of_copies > contract.max_number_of_copies:
                raise ValidationError(_(
                    'Min Number of Copies (%(minimum)s) cannot be greater than '
                    'Max Number of Copies (%(maximum)s).',
                    minimum=contract.min_number_of_copies,
                    maximum=contract.max_number_of_copies,
                ))

    @api.constrains(*CONTRACT_FIELDS)
    def _check_duplicate(self):
        """No two contracts may hold exactly the same data - that is the same
        contract entered twice. Contracts differing in any single field are
        fine.
        """
        for contract in self:
            domain = [('id', '!=', contract.id)]
            for field_name in CONTRACT_FIELDS:
                value = contract[field_name]
                if contract._fields[field_name].type == 'many2one':
                    value = value.id
                domain.append((field_name, '=', value))
            duplicate = self.search(domain, limit=1)
            if duplicate:
                raise ValidationError(_(
                    'Another Service Contract already holds exactly this data '
                    '(%(contract)s). Change something on it, or use the '
                    'existing one.',
                    contract=duplicate.display_name,
                ))
