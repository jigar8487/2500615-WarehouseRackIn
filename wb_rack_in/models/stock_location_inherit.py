from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    # ========== FIELDS ==========
    is_staging_location = fields.Boolean("Staging Location", default=False)

