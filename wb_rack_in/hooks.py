from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Post-installation hook to set up initial data and migrate existing users"""
    
    # Migrate existing rack-in users to mobile_only type
    existing_users = env['rack.in.user.management'].search([])
    for user in existing_users:
        # Set all existing users as mobile_only type if not already set
        if not user.user_type:
            user.write({'user_type': 'mobile_only'})
    
    # Create rack-in users for inventory managers (if they don't exist already)
    inventory_admin_group = env.ref('stock.group_stock_manager', raise_if_not_found=False)
    
    if inventory_admin_group:
        # Search for users in that group
        users = env['res.users'].search([('groups_id', 'in', inventory_admin_group.id)])
        
        for user in users:
            # Check if user is already linked
            existing = env['rack.in.user.management'].search([
                ('odoo_user_id', '=', user.id),
                ('user_type', '=', 'odoo_linked')
            ])
            
            if not existing:
                # Create new odoo_linked user
                env['rack.in.user.management'].create({
                    'user_type': 'odoo_linked',
                    'odoo_user_id': user.id,
                    'user_name': user.name,
                    'email': user.email or user.login,
                    'role': 'manager',
                })


def post_update_hook(env):
    """Post-update hook to handle module upgrades"""
    # Set user_type for any users that don't have it set
    users_without_type = env['rack.in.user.management'].search([
        '|', ('user_type', '=', False), ('user_type', '=', '')
    ])
    
    for user in users_without_type:
        # Default to mobile_only for existing users
        user.write({'user_type': 'mobile_only'})

