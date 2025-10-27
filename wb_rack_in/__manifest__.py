{
    'name': 'Warehouse RackIn',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Complete Warehouse RackIn workflow with mobile API and dashboard',
    'license': 'LGPL-3',
    'description': '''
        Warehouse RackIn Workflow Management
        ====================================
        
        This unified module provides:
        * Complete RackIn operations from staging to racks
        * Mobile API support for warehouse applications
        * Web dashboard for monitoring and analytics
        * Barcode scanning support
        
        * Real-time inventory validation
        * Complete traceability and logging
        * Role-based access control
        
        API Endpoints:
        * POST /api/v1/mobile/login - User authentication with PIN
        * POST /api/v1/mobile/rack-in/validate-location - Validate rack location by barcode/name
        * POST /api/v1/mobile/rack-in/validate-product - Validate product and get staging qty
        * POST /api/v1/mobile/rack-in/submit - Submit rackin operation with products
        * POST /wb_rack_in/statistics - Dashboard statistics
    ''',
    'author': 'Wan Buffer Services',
    'developer': 'Wan Buffer Services Team',
    'depends': ['base', 'web', 'stock', 'purchase', 'mail'],
    'data': [
        'security/ir.model.access.csv',

        'views/rack_in_log_views.xml',
        'views/stock_location_view_inherit.xml',
        'views/rack_in_user_management.xml',
        'views/rack_in_dashboard_template.xml',

        'data/rack_in_sequence.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'wb_rack_in/static/src/rack_in_dashboard_loader.js',
            'wb_rack_in/static/src/rack_in_list_dashboard.js',
        ],
        'web.assets_qweb': [
            'wb_rack_in/static/src/dashboard_template.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'post_update_hook': 'post_update_hook',
    'installable': True,
    'auto_install': False,
    'application': True,
}
