from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
from html import unescape
from odoo.tools import html2plaintext
from odoo.tools import html_escape
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError


class RackInLog(models.Model):
    _name = 'rack.in.log'
    _description = 'Rack In Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'rack_process'

    # ========== FIELDS ==========
    rack_process = fields.Char(string="Record Number",
                               readonly=True, copy=False, default='New')
    rack_location_id = fields.Many2one('stock.location', string='Rack Location', required=True)
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
        domain=[
            ('usage', '=', 'internal'),
            ('is_staging_location', '=', True),
            ('active', '=', True)
        ]
    )
    performed_by = fields.Many2one('res.users', string='Performed By (Odoo User)',
                                   default=lambda self: self.env.user, readonly=True)
    performed_by_user = fields.Many2one('rack.in.user.management', string='Performed By',
                                        readonly=True, help='The rack-in user who performed this operation')
    performed_by_display = fields.Char(string='Performed By', compute='_compute_performed_by_display', store=True)
    status = fields.Selection([('normal', 'Normal')],
                              string='Status', compute='_compute_status',
                              store=True, default='normal', readonly=True)
    operation_source = fields.Selection([('web', 'Web'), ('app', 'App')],
                                        string='Operation Source', required=True)
    date_time = fields.Datetime(string='Date & Time', default=fields.Datetime.now)
    status_html = fields.Html(string='Status', compute='_compute_status_html', sanitize=False)
    source_html = fields.Html(string='Source', compute='_compute_source_html', sanitize=False)
    source_quant_id = fields.Many2one('stock.quant', string='Source Quant')
    rack_in_log_line_ids = fields.One2many(
        'rack.in.log.line',
        'rack_in_log_id',
        string='Rack In Log Lines',
    )

    rack_quant_id = fields.Many2one(
        'stock.quant',
        compute='_compute_rack_quant',
        string="Rack Quant",
        store=False  # Optional: Set to True if needed
    )

    @api.depends('rack_location_id', 'rack_in_log_line_ids.product_id')
    def _compute_rack_quant(self):
        Quant = self.env['stock.quant'].sudo()
        for rec in self:
            if not rec.rack_location_id:
                rec.rack_quant_id = False
                continue

            product_ids = rec.rack_in_log_line_ids.mapped('product_id').ids
            quant = Quant.search([
                ('product_id', 'in', product_ids),
                ('location_id', '=', rec.rack_location_id.id)
            ], limit=1)

            rec.rack_quant_id = quant

    # ========== DEFAULT CREATE ==========
    @api.model
    def create(self, vals):
        if vals.get('rack_process', 'New') == 'New':
            vals['rack_process'] = self.env['ir.sequence'].next_by_code('rack.in.log') or '/'
        return super(RackInLog, self).create(vals)

    # ========== PERFORMED BY DISPLAY COMPUTATION ==========
    @api.depends('performed_by_user', 'performed_by')
    def _compute_performed_by_display(self):
        """
        Display the rack-in user name if available, otherwise fall back to Odoo user
        """
        for rec in self:
            if rec.performed_by_user:
                rec.performed_by_display = rec.performed_by_user.user_name
            elif rec.performed_by:
                rec.performed_by_display = rec.performed_by.name
            else:
                rec.performed_by_display = 'Unknown'

    # ========== STATUS COMPUTATION ==========
    @api.depends('rack_in_log_line_ids.put_qty', 'rack_in_log_line_ids.staging_qty')
    def _compute_status(self):
        """All operations are considered normal since quantity validation prevents discrepancies."""
        for rec in self:
            rec.status = 'normal'


    def action_rack_in(self):
        """Transfer stock from source to rack location and update stock.quant."""
        Quant = self.env['stock.quant'].sudo()

        for line in self.rack_in_log_line_ids:
            product = line.product_id
            put_qty = line.put_qty

            if put_qty <= 0:
                continue  # Skip lines with no quantity

            # --- Decrease from Source Location ---
            source_quant = Quant.search([
                ('product_id', '=', product.id),
                ('location_id', '=', self.source_location_id.id)
            ], limit=1)


            source_quant.quantity -= put_qty

            # --- Add to Rack Location ---
            rack_quant = Quant.search([
                ('product_id', '=', product.id),
                ('location_id', '=', self.rack_location_id.id)
            ], limit=1)

            if rack_quant:
                rack_quant.quantity += put_qty
            else:
                Quant.create({
                    'product_id': product.id,
                    'location_id': self.rack_location_id.id,
                    'quantity': put_qty,
                })

        return True


    

    # ========== STATUS BADGE HTML ==========
    @api.depends('status')
    def _compute_status_html(self):
        for rec in self:
            rec.status_html = '<span style="background-color:#28a745;color:white;padding:5px 6px;border-radius:11px; font-weight:bold;">Normal</span>'

    # ========== SOURCE BADGE HTML ==========
    @api.depends('operation_source')
    def _compute_source_html(self):
        for rec in self:
            if rec.operation_source == 'web':
                rec.source_html = '<span style="background-color:#007bff;color:white;padding:5px 6px;border-radius:11px; font-weight:bold;">Web</span>'
            elif rec.operation_source == 'app':
                rec.source_html = '<span style="background-color:#E9EFFD;color:black;padding:3px 6px;border-radius:11px; font-weight:bold;">App</span>'
            else:
                rec.source_html = ''

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.today()
        domain = [('create_date', '>=', fields.Datetime.today().replace(hour=0, minute=0, second=0))]
        records = self.search(domain)

        return {
            'total_operations': len(records),
            'total_quantity': sum(records.mapped('rack_in_log_line_ids.put_qty')) if records else 0,
        }

     # ========== Constraint: Rack Location and Source Location must be different ==========
    @api.constrains('rack_location_id', 'source_location_id')
    def _check_different_locations(self):
        for line in self:
            if line.rack_location_id and line.source_location_id and line.rack_location_id.id == line.source_location_id.id:
                raise ValidationError(_("Rack Location and Source Location cannot be the same."))

    # ========== OVERRIDE UNLINK ==========
    def unlink(self):
        """Prevent deletion of executed rack-in operations"""
        for record in self:
            if record.rack_quant_id:
                raise UserError(_(
                    'Cannot delete rack-in operation "%s" because it has already been executed. '
                    'Stock has been moved to the rack location.' % record.rack_process
                ))
        return super(RackInLog, self).unlink()