from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContractType(models.Model):
    _name = 'infinity.contract.type'
    _description = 'Contract Type'

    # Technical field name stays "abbreviation", but it now shows the
    # contract type's full name - "name" is the short abbreviation instead
    # (see below), swapped at the user's request.
    abbreviation = fields.Selection([
        ('warranty', 'Warranty'),
        ('labor_annual_contract', 'Labor Annual Contract'),
        ('service_maintenance_annual_contract', 'Service Maintenance Annual Contract'),
        ('full_service_maintenance_annual_contract', 'Full Service Maintenance Annual Contract'),
        ('cost_per_click', 'Cost Per Click'),
        ('time_material', 'Time & Material'),
    ], string='Full Name', required=True)

    # Read-only, and deliberately NOT required: it is always derived from
    # "abbreviation" (Full Name) below, which is required, so marking this
    # required too adds nothing - it only lets a legacy row with a blank
    # abbreviation abort the whole module load (and roll back the very
    # migration meant to clean that row up).
    name = fields.Selection([
        ('w', 'W'),
        ('labor', 'Labor'),
        ('sma', 'S.M.A'),
        ('fsma', 'F.S.M.A'),
        ('cpp', 'CPP'),
        ('tm', 'T&M'),
    ], string='Abbreviation', compute='_compute_name', store=True)

    _ABBREVIATION_BY_FULL_NAME = {
        'warranty': 'w',
        'labor_annual_contract': 'labor',
        'service_maintenance_annual_contract': 'sma',
        'full_service_maintenance_annual_contract': 'fsma',
        'cost_per_click': 'cpp',
        'time_material': 'tm',
    }

    @api.depends('abbreviation')
    def _compute_name(self):
        for record in self:
            record.name = record._ABBREVIATION_BY_FULL_NAME.get(record.abbreviation, False)

    # Each abbreviation has its own SLA Sub Type field with only the values
    # that belong to it, shown (see the view) only when that abbreviation is
    # selected.
    warranty_sub_type = fields.Selection([
        ('w_supplier', 'W-Supplier'),
        ('w_infinity', 'W-Infinity'),
        ('w_service_provider', 'W-Service Provider'),
        ('w_extend_infinity', 'W-Extend-Infinity'),
        ('w_extend_service_provider', 'W-Extend-Service Provider'),
    ], string='SLA Sub Type')
    labor_sub_type = fields.Selection([
        ('labor_visits', 'Labor Visits'),
        ('labor_hours', 'Labor Hours'),
    ], string='SLA Sub Type')
    service_maintenance_sub_type = fields.Selection([
        ('service_maintenance_annual_contract', 'Service Maintenance Annual Contract'),
    ], string='SLA Sub Type')
    fsma_sub_type = fields.Selection([
        ('fsma_d', 'F.S.M.A (Default)'),
        ('fsma_to', 'F.S.M.A (Toner Out)'),
        ('fsma_md', 'F.S.M.A (Media In)'),
    ], string='SLA Sub Type')
    cost_per_click_sub_type = fields.Selection([
        ('leasing_insourcing', 'Leasing Insourcing - Cost Per Click'),
        ('leasing_outsourcing', 'Leasing Outsourcing - Cost Per Click'),
        ('rental_insourcing', 'Rental Insourcing - Cost Per Click'),
        ('rental_outsourcing', 'Rental Outsourcing - Cost Per Click'),
    ], string='SLA Sub Type')
    time_material_sub_type = fields.Selection([
        ('time_material', 'Time & Material'),
    ], string='SLA Sub Type')

    # Whichever of the fields above actually applies for this record's
    # abbreviation, collapsed into one technical value. Service Contract
    # reads this (via a related field) to drive its own field visibility,
    # so every existing condition keeps working unchanged.
    sub_type_value = fields.Char(string='SLA Sub Type Value', compute='_compute_sub_type_value', store=True)

    _SUB_TYPE_FIELD_BY_ABBREVIATION = {
        'warranty': 'warranty_sub_type',
        'labor_annual_contract': 'labor_sub_type',
        'service_maintenance_annual_contract': 'service_maintenance_sub_type',
        'full_service_maintenance_annual_contract': 'fsma_sub_type',
        'cost_per_click': 'cost_per_click_sub_type',
        'time_material': 'time_material_sub_type',
    }

    def _sub_type_label(self):
        """Human label of whichever Sub Type field applies to this record."""
        self.ensure_one()
        field_name = self._SUB_TYPE_FIELD_BY_ABBREVIATION.get(self.abbreviation)
        if not field_name:
            return False
        value = self[field_name]
        if not value:
            return False
        return dict(self._fields[field_name].selection).get(value)

    @api.depends('abbreviation', 'name', 'warranty_sub_type', 'labor_sub_type',
                 'service_maintenance_sub_type', 'fsma_sub_type',
                 'cost_per_click_sub_type', 'time_material_sub_type')
    def _compute_display_name(self):
        """Show the record by its SLA Sub Type, so every dropdown pointing at
        a Contract Type (Service Contract's, and Sales Order's through it)
        lists sub types rather than the short abbreviation.
        """
        full_names = dict(self._fields['abbreviation'].selection)
        for record in self:
            record.display_name = (
                record._sub_type_label()
                or full_names.get(record.abbreviation)
                or ''
            )

    @api.depends('abbreviation', 'warranty_sub_type', 'labor_sub_type',
                 'service_maintenance_sub_type', 'fsma_sub_type',
                 'cost_per_click_sub_type', 'time_material_sub_type')
    def _compute_sub_type_value(self):
        for record in self:
            field_name = record._SUB_TYPE_FIELD_BY_ABBREVIATION.get(record.abbreviation)
            record.sub_type_value = getattr(record, field_name) if field_name else False

    @api.constrains('abbreviation', 'warranty_sub_type', 'labor_sub_type',
                    'service_maintenance_sub_type', 'fsma_sub_type',
                    'cost_per_click_sub_type', 'time_material_sub_type')
    def _check_duplicate(self):
        """A contract type is its Full Name and its SLA Sub Type - there is
        no sense in two records saying the same thing. Comparing
        sub_type_value rather than the six sub type fields keeps this to the
        one that actually applies.
        """
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('abbreviation', '=', record.abbreviation),
                ('sub_type_value', '=', record.sub_type_value),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'A Contract Type for %(full_name)s / %(sub_type)s already '
                    'exists.',
                    full_name=dict(record._fields['abbreviation'].selection).get(
                        record.abbreviation) or record.abbreviation,
                    sub_type=record._sub_type_label() or '-',
                ))
