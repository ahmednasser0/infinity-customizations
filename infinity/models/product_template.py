from odoo import fields, models


class ProductTemplate(models.Model):
    """Where a machine's model and manufacturer are answered.

    They used to be typed on each Technical Report, which meant the same
    machine could be a KM-C3320i on one visit and a KMC3320i on the next,
    and neither was wrong because neither was checked. Answered on the
    product, there is one answer, and every report reads it.

    The names carry the infinity_ prefix because product.template is a model
    half of Odoo extends: a field called plainly manufacturer would be a
    coin toss between adjusting somebody else's and inventing a second one
    that shadows it.
    """
    _inherit = 'product.template'

    infinity_machine_model = fields.Char(string='Machine Model')
    infinity_manufacturer = fields.Char(string='Manufacturer')


class ProductProduct(models.Model):
    """The two fields as a variant reads them.

    Technical Reports find the machine through its serial, and a serial
    belongs to a product.product, not to the template above it - so the
    variant has to be able to answer for itself.
    """
    _inherit = 'product.product'

    # Writable on purpose, which for a related field means writing back to
    # the template. That is right here and not a mistake to be corrected
    # later: a machine's model and make belong to the product, not to one
    # of its variants, so the template is where the answer is meant to
    # land.
    #
    # It is also the only way to type them from where people actually
    # stand. A Bill of Materials line names a product.product, so clicking
    # through to the component ticked Engine opens the variant form - and
    # that form is product_normal_form_view, which is a primary view
    # inheriting the template's, so it already shows the Machine page. The
    # page was there and the two boxes in it were grey, which is what made
    # the value impossible to set.
    infinity_machine_model = fields.Char(
        related='product_tmpl_id.infinity_machine_model', readonly=False)
    infinity_manufacturer = fields.Char(
        related='product_tmpl_id.infinity_manufacturer', readonly=False)

    def _infinity_engine_product(self):
        """The Engine component of this kit, or nothing where it is not one.

        A Sales Kit is sold as one thing and built of many, and the one
        ticked Engine on its Bill of Materials is the machine - so that is
        where its model and make are answered.

        A product that is not a kit returns nothing on purpose, rather than
        returning itself. The caller uses that to tell the two cases apart:
        a kit answers for itself, and anything else is left for somebody to
        type.
        """
        self.ensure_one()
        Bom = self.env.get('mrp.bom')
        if Bom is None:
            return self.env['product.product']
        found = Bom._bom_find(self, company_id=self.env.company.id,
                              bom_type='phantom')
        bom = found.get(self)
        if not bom:
            return self.env['product.product']
        return bom.bom_line_ids.filtered('engine')[:1].product_id

    def _infinity_machine_product(self):
        """The product that answers for the machine, starting from this one.

        Two cases, and the second is the one that actually turns up.

        A Sales Kit answers with the component ticked Engine on its Bill
        of Materials.

        A product that is itself ticked Engine on some kit's Bill of
        Materials answers with itself. A serial number belongs to the
        machine, not to the kit it was sold inside, so the lot on the
        order line is the Engine's lot and the product reached through it
        is the Engine - and asking the Engine for its own Engine returned
        nothing, which is why the model and the make arrived empty and the
        fields stayed open. It is a machine; it answers for itself.

        Anything else answers with nothing, and is somebody's to type.
        """
        self.ensure_one()
        engine = self._infinity_engine_product()
        if engine:
            return engine
        Line = self.env.get('mrp.bom.line')
        if Line is not None and Line.search_count(
                [('product_id', '=', self.id), ('engine', '=', True)],
                limit=1):
            return self
        return self.env['product.product']
