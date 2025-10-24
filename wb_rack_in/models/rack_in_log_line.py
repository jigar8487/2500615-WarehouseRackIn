from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RackInLogLine(models.Model):
    _name = 'rack.in.log.line'
    _description = 'Rack In Log Line'
    _rec_name = 'product_id'

    # ========== FIELDS ==========
    rack_in_log_id = fields.Many2one('rack.in.log', string='Rack In Log',
                                     required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
                                 required=True)
    product_ids = fields.Many2many(
        'product.product', string='Source Location Products',
        compute="_compute_product_ids",
        store=True
    )
    put_qty = fields.Float(string='Put Quantity', required=True)
    staging_qty = fields.Float(string='Staging Quantity', required=True)

    # ========== Compute Source Location Products ==========
    @api.depends('rack_in_log_id.source_location_id')
    def _compute_product_ids(self):
        """
        Compute available products from current stock in source location.
        Only products with qty > 0 will be included.
        """
        StockQuant = self.env['stock.quant']
        for line in self:
            if line.rack_in_log_id.source_location_id:
                location = line.rack_in_log_id.source_location_id
                print("\n\n\nComputing products for location:", location.name)
                quants = StockQuant.search([
                    ('location_id', '=', location.id),
                    ('quantity', '>', 0)
                ])

                line.product_ids = quants.mapped('product_id')
            else:
                line.product_ids = False

    # ========== Auto-fill Staging Quantity Based on Product and Source Location ==========
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            source_location = line.rack_in_log_id.source_location_id
            if line.product_id and source_location:
                # Check if the location has staging_location = True
                if source_location.is_staging_location:
                    quant = self.env['stock.quant'].search([
                        ('product_id', '=', line.product_id.id),
                        ('location_id', '=', source_location.id)
                    ], limit=1)
                    line.staging_qty = quant.quantity if quant else 0.0
                else:
                    line.staging_qty = 0.0
            else:
                line.staging_qty = 0.0

    # ========== Constrain: Put Quantity must be ≥ 0 and ≤ Staging Quantity ==========
    @api.constrains('put_qty', 'staging_qty')
    def _check_put_qty_valid(self):
        for line in self:
            if line.put_qty < 0:
                raise ValidationError("Put Quantity cannot be negative.")
            if line.put_qty == 0:
                raise ValidationError("Please add Put Quantity (cannot be 0).")
            if line.put_qty > line.staging_qty:
                raise ValidationError(
                    f"Put Quantity ({line.put_qty}) cannot be greater than Staging Quantity ({line.staging_qty})."
                )
