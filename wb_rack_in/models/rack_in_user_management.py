from odoo import models, fields, api , _,  SUPERUSER_ID
from odoo.exceptions import ValidationError
import random
import re


class RackInUserManagement(models.Model):
    _name = 'rack.in.user.management'
    _description = 'Rack In User Management - All Users Stored in Database'
    _rec_name = 'user_name'
    _rec_names_search = ['user_name', 'email']

    # ========== FIELDS ==========
    user_type = fields.Selection([
        ('mobile_only', 'Mobile User'),
        ('odoo_linked', 'Odoo User')
    ], string='User Type', required=True, default='mobile_only', tracking=True)
    
    # For Odoo linked users  
    odoo_user_id = fields.Many2one(
        'res.users', 
        string='Odoo User',
        domain="[('active', '=', True), ('share', '=', False), ('id', 'not in', existing_odoo_user_ids)]"
    )
    existing_odoo_user_ids = fields.Many2many('res.users', compute='_compute_existing_odoo_users')
    
    # All user data stored directly in database (no external JSON)
    user_name = fields.Char(string='User Name', store=True, required=True)
    role = fields.Selection([('picker', 'Picker'),('manager', 'Manager')],
                            string='Role', required=True, default='picker')
    email = fields.Char(string='Email', store=True, required=True)
    pin_code_number = fields.Char(string='PIN Code', size=4, readonly=True,
                                  tracking=True, 
                                  default=lambda self: self._generate_pin())
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Keep for backward compatibility
    partner_id = fields.Many2one('res.partner', string='Related Customer', readonly=True)

    @api.model
    def _get_available_odoo_users_domain(self):
        """Get domain for available Odoo users (not already linked)"""
        # Get all linked user IDs
        linked_user_ids = self.search([
            ('user_type', '=', 'odoo_linked'),
            ('odoo_user_id', '!=', False)
        ]).mapped('odoo_user_id.id')
        
        return [
            ('active', '=', True),
            ('id', 'not in', linked_user_ids)
        ]

    # ========== COMPUTED FIELDS ==========
    def _compute_existing_odoo_users(self):
        """Compute existing linked Odoo users to exclude from dropdown (only Internal Users)"""
        for record in self:
            try:
                # Get all linked Odoo users, excluding current record if it's being edited
                domain = [
                    ('user_type', '=', 'odoo_linked'),
                    ('odoo_user_id', '!=', False)
                ]
                
                # If this is an existing record (has a real ID), exclude it from the search
                if record.id and isinstance(record.id, int):
                    domain.append(('id', '!=', record.id))
                
                existing_records = self.search(domain)
                existing_user_ids = existing_records.mapped('odoo_user_id.id')
                
                # Filter out Portal users from existing linked users
                # Only consider Internal Users (share=False) as truly "existing"
                if existing_user_ids:
                    internal_existing_users = self.env['res.users'].search([
                        ('id', 'in', existing_user_ids),
                        ('share', '=', False)  # Only Internal Users
                    ])
                    existing_user_ids = internal_existing_users.ids
                
                record.existing_odoo_user_ids = [(6, 0, existing_user_ids)]
            except Exception as e:
                # Fallback: empty list if there's any issue
                record.existing_odoo_user_ids = [(6, 0, [])]

    # ========== ONCHANGE METHODS ==========
    @api.onchange('user_type')
    def _onchange_user_type(self):
        """Clear fields when user type changes and return domain for odoo_user_id"""
        if self.user_type == 'mobile_only':
            self.odoo_user_id = False
        elif self.user_type == 'odoo_linked':
            # Keep user_name and email for editing if needed
            pass
        
        # Return domain for odoo_user_id field to limit available users
        if self.user_type == 'odoo_linked':
            # Get all linked Odoo users (excluding current record)
            domain_filter = [
                ('user_type', '=', 'odoo_linked'),
                ('odoo_user_id', '!=', False)
            ]
            
            # Exclude current record if editing existing record
            if self.id and isinstance(self.id, int):
                domain_filter.append(('id', '!=', self.id))
            
            linked_records = self.search(domain_filter)
            linked_user_ids = linked_records.mapped('odoo_user_id.id')
            
            # Filter out Portal users from linked users - only consider Internal Users as truly "linked"
            if linked_user_ids:
                internal_linked_users = self.env['res.users'].search([
                    ('id', 'in', linked_user_ids),
                    ('share', '=', False)  # Only Internal Users
                ])
                linked_user_ids = internal_linked_users.ids
            
            # Get base users group (Internal Users)
            base_users_group = self.env.ref('base.group_user', raise_if_not_found=False)
            
            # Only show Internal Users with proper filtering
            domain_conditions = [
                ('active', '=', True), 
                ('share', '=', False),  # Only Internal Users, exclude Portal users
                ('id', 'not in', linked_user_ids)
            ]
            
            # Additional group-based filtering if base users group exists
            if base_users_group:
                domain_conditions.append(('groups_id', 'in', [base_users_group.id]))
            
            domain = {'odoo_user_id': domain_conditions}
            return {'domain': domain}
        
        return {}

    @api.onchange('odoo_user_id')
    def _onchange_odoo_user_id(self):
        """Auto-populate user details when Odoo user is selected"""
        if self.odoo_user_id and self.user_type == 'odoo_linked':
            self.user_name = self.odoo_user_id.name
            self.email = self.odoo_user_id.email or self.odoo_user_id.login

    @api.onchange('role')
    def _onchange_role(self):
        """Clear PIN when role changes to Manager"""
        if self.role == 'manager':
            self.pin_code_number = False
        elif self.role == 'picker' and not self.pin_code_number:
            # Generate PIN for pickers if not present
            self.pin_code_number = self._generate_pin()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """Override to dynamically set domain for odoo_user_id field"""
        result = super().fields_view_get(view_id, view_type, toolbar, submenu)
        return result

    # ========== EMAIL FORMAT VALIDATION ==========
    @api.constrains('email', 'role', 'user_type')
    def _check_email_format(self):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        for record in self:
            if record.email and not re.match(pattern, record.email):
                raise ValidationError(_("Invalid email format. Please enter a valid email address."))

    # ========== USER TYPE VALIDATION ==========
    @api.constrains('user_type', 'odoo_user_id', 'user_name', 'email')
    def _check_user_type_requirements(self):
        """Validate requirements based on user type"""
        for record in self:
            if record.user_type == 'odoo_linked':
                if not record.odoo_user_id:
                    raise ValidationError(_("Odoo User is required for linked users."))
                # Check for duplicate Odoo user linking
                existing = self.search([
                    ('id', '!=', record.id),
                    ('user_type', '=', 'odoo_linked'),
                    ('odoo_user_id', '=', record.odoo_user_id.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(_("This Odoo user is already linked to another rack-in user."))
            elif record.user_type == 'mobile_only':
                if not record.user_name:
                    raise ValidationError(_("User Name is required for mobile users."))
                if not record.email:
                    raise ValidationError(_("Email is required for mobile users."))

    @api.model
    def _generate_pin(self):
        # Generate a random 4-digit PIN as string
        return str(random.randint(1000, 9999))

    @api.constrains('pin_code_number')
    def _check_pin_code(self):
        for record in self:
            # PIN is only required for Pickers, not for Managers
            if record.role == 'picker' and not record.pin_code_number:
                raise ValidationError(_('PIN Code is required for Picker role.'))
            
            # Check for duplicate PIN (only if PIN exists)
            if record.pin_code_number:
                duplicate = self.search([
                    ('id', '!=', record.id),
                    ('pin_code_number', '=', record.pin_code_number)
                ])
                if duplicate:
                    raise ValidationError(_('The PIN Code must be unique.'))

    def action_reset_pin_code_number(self):
        """Reset PIN code for any user type"""
        for record in self:
            # Generate new unique PIN
            new_pin = self._generate_pin()
            while self.search([('pin_code_number', '=', new_pin), ('id', '!=', record.id)]):
                new_pin = self._generate_pin()
            record.pin_code_number = new_pin

    # ========== ARCHIVE METHODS ==========
    def action_archive(self):
        """Archive users"""
        return self.write({'active': False})

    def action_unarchive(self):
        """Unarchive users"""
        return self.write({'active': True})

    # ========== OVERRIDE CREATE ==========
    @api.model
    def create(self, vals):
        user_type = vals.get('user_type', 'mobile_only')
        
        if user_type == 'mobile_only':
            # All mobile user data is stored directly in the database
            # No partner needed for mobile users
            vals.pop('partner_id', None)
                
        elif user_type == 'odoo_linked':
            # Handle Odoo user linking
            if vals.get('odoo_user_id'):
                odoo_user = self.env['res.users'].browse(vals['odoo_user_id'])
                vals['user_name'] = odoo_user.name
                vals['email'] = odoo_user.email or odoo_user.login
                
                # Create partner for Odoo users for backward compatibility
                partner = self.env['res.partner'].create({
                    'name': vals.get('user_name'),
                    'email': vals.get('email'),
                    'is_company': False,
                    'customer_rank': 1,
                })
                vals['partner_id'] = partner.id
        
        # Create the Odoo record
        record = super(RackInUserManagement, self).create(vals)
        return record

    # ========== OVERRIDE WRITE ==========
    def write(self, vals):
        """Handle updates, especially when changing user type"""
        for record in self:
            # If changing to odoo_linked and odoo_user_id is provided
            if vals.get('user_type') == 'odoo_linked' and vals.get('odoo_user_id'):
                odoo_user = self.env['res.users'].browse(vals['odoo_user_id'])
                vals['user_name'] = odoo_user.name
                vals['email'] = odoo_user.email or odoo_user.login
            
            # Update partner if name or email changes
            if 'user_name' in vals or 'email' in vals:
                if record.partner_id:
                    partner_vals = {}
                    if 'user_name' in vals:
                        partner_vals['name'] = vals['user_name']
                    if 'email' in vals:
                        partner_vals['email'] = vals['email']
                    if partner_vals:
                        record.partner_id.write(partner_vals)
        
        return super(RackInUserManagement, self).write(vals)

    # ========== OVERRIDE UNLINK ==========
    def unlink(self):
        """Handle deletion by archiving instead of permanently deleting"""
        # Archive in Odoo (set active=False) instead of deleting
        return self.write({'active': False})

    # ========== DISPLAY METHODS ==========
    def name_get(self):
        """Custom display name with user type indication"""
        result = []
        for record in self:
            user_type_label = "📱" if record.user_type == 'mobile_only' else "🔗"
            name = f"{user_type_label} {record.user_name} ({record.role.title()})"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search to include email and role"""
        args = args or []
        if name:
            args = ['|', '|', 
                    ('user_name', operator, name),
                    ('email', operator, name),
                    ('role', operator, name)] + args
        return super(RackInUserManagement, self)._name_search(
            '', args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)




