# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
 

_logger = logging.getLogger(__name__)


class MobileAuthAPI(http.Controller):
    """
    Mobile Authentication API for Rack-In Users
    Supports both Mobile and Odoo users with Picker role and PIN Code
    """

    @http.route('/api/v1/mobile/login', type='json', auth='none', methods=['POST'], csrf=False)
    def mobile_login(self, database=None, pin_code=None, **kwargs):
        """
        Mobile User Login API
        
        Authenticates a mobile user (Picker) using database and PIN code
        Supports both Mobile-Only users and Odoo users with Picker role
        
        Request:
        {
            "database": "<database_name>",
            "pin_code": "<user_pin>"
        }
        
        Response on Success:
        {
            "success": true,
            "message": "Login successful",
            "user": {
                "id": <user_id>,                    # Database record ID
                "name": "<user_name>",              # User's full name
                "email": "<user_email>",            # User's email
                "role": "picker",                   # User's role
                "pin_code": "<user_pin>",           # User's PIN code
                "user_type": "mobile_only|odoo_linked"
            },
            "staging_locations": [                  # Active staging locations
                {
                    "id": <location_id>,
                    "name": "<location_name>",
                    "complete_name": "<full_path>",
                    "barcode": "<barcode>"
                }
            ]
        }
        
        Response on Failure:
        {
            "success": false,
            "error": "Invalid URL" | "Invalid Database" | "Invalid PIN Code"
        }
        """
        try:
            # Validate Database
            if not database:
                _logger.warning("Login failed: Database not provided")
                return {
                    'success': False,
                    'error': 'Invalid Database'
                }
            
            # Set database context directly without checking existence
            # The database is already determined by the URL, checking would require system permissions
            request.session.db = database
            
            # Validate PIN Code
            if not pin_code:
                _logger.warning("Login failed: PIN code not provided")
                return {
                    'success': False,
                    'error': 'Invalid PIN Code'
                }
            
            # Set database context
            request.session.db = database
            
            # Search for user with matching PIN
            # Allow both Mobile and Odoo users with Picker role and PIN Code
            try:
                env = request.env(user=1)  # Use admin user for search
                
                user_record = env['rack.in.user.management'].sudo().search([
                    ('pin_code_number', '=', pin_code),
                    ('active', '=', True),
                    ('role', '=', 'picker')
                    # Removed user_type filter - now accepts both 'mobile_only' and 'odoo_linked'
                ], limit=1)
                
                if not user_record:
                    _logger.warning(f"Login failed: Invalid PIN '{pin_code}' for database '{database}'")
                    return {
                        'success': False,
                        'error': 'Invalid PIN Code'
                    }
                
                # Success! (Works for both Mobile and Odoo users)
                _logger.info(f"Login successful: {user_record.user_name} (Type: {user_record.user_type}, PIN: {pin_code})")
                
                # Get staging locations (only active locations with is_staging_location = True)
                staging_locations = env['stock.location'].sudo().search([
                    ('is_staging_location', '=', True),
                    ('active', '=', True),
                    ('usage', '=', 'internal')
                ])
                
                staging_locations_data = []
                for location in staging_locations:
                    staging_locations_data.append({
                        'id': location.id,
                        'name': location.name,
                        'complete_name': location.complete_name,
                        'barcode': location.barcode or ''
                    })
                
                _logger.info(f"Found {len(staging_locations_data)} active staging locations")
                
                # Return user data - use database record ID for all users
                return {
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'id': user_record.id,  # Database record ID (works for both types)
                        'name': user_record.user_name,
                        'email': user_record.email,
                        'role': user_record.role,
                        'pin_code': user_record.pin_code_number,
                        'user_type': user_record.user_type  # mobile_only or odoo_linked
                    },
                    'staging_locations': staging_locations_data
                }
                
            except Exception as e:
                _logger.error(f"Database query error: {str(e)}")
                return {
                    'success': False,
                    'error': 'Invalid PIN Code'
                }
                
        except Exception as e:
            _logger.error(f"Mobile login error: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid URL'
            }

    @http.route('/api/v1/mobile/logout', type='json', auth='user', methods=['POST'], csrf=False)
    def mobile_logout(self, **kwargs):
        """
        Mobile User Logout API
        
        Response:
        {
            "success": true,
            "message": "Logout successful"
        }
        """
        try:
            request.session.logout(keep_db=True)
            return {
                'success': True,
                'message': 'Logout successful'
            }
        except Exception as e:
            _logger.error(f"Logout error: {str(e)}")
            return {
                'success': False,
                'error': 'Logout failed'
            }


class MobileRackInAPI(http.Controller):
    """
    Mobile Rack-In Operation APIs
    Handles rack location validation, product validation, and rack-in submission
    """

    @http.route('/api/v1/mobile/rack-in/validate-location', type='json', auth='none', methods=['POST'], csrf=False)
    def validate_rack_location(self, location_identifier=None, **kwargs):
        """
        Validate Rack Location API
        
        Validates if a rack location exists by barcode or name
        
        Request:
        {
            "location_identifier": "<barcode_or_location_name>"
        }
        
        Response on Success:
        {
            "success": true,
            "location": {
                "id": <location_id>,
                "name": "<location_name>",
                "complete_name": "<full_location_path>",
                "barcode": "<location_barcode>",
                "usage": "internal"
            }
        }
        
        Response on Failure:
        {
            "success": false,
            "error": "Location not found" | "Location identifier required"
        }
        """
        try:
            
            # Validate location identifier
            if not location_identifier:
                _logger.warning("Validate location failed: Location identifier not provided")
                return {
                    'success': False,
                    'error': 'Location identifier required'
                }
            
            # Use database from session (set during login)
            if not request.session.db:
                _logger.warning("Validate location failed: No database in session")
                return {
                    'success': False,
                    'error': 'Session expired. Please login again.'
                }
            
            try:
                env = request.env(user=1)  # Use admin user for search
                
                # Search by barcode first, then by name
                location = env['stock.location'].sudo().search([
                    '|',
                    ('barcode', '=', location_identifier),
                    ('name', '=', location_identifier),
                    ('usage', '=', 'internal'),
                    ('active', '=', True)
                ], limit=1)
                
                if not location:
                    _logger.warning(f"Validate location failed: Location '{location_identifier}' not found")
                    return {
                        'success': False,
                        'error': 'Location not found'
                    }
                
                # Success! Return location details
                _logger.info(f"Location validated: {location.complete_name} (ID: {location.id})")
                
                return {
                    'success': True,
                    'location': {
                        'id': location.id,
                        'name': location.name,
                        'complete_name': location.complete_name,
                        'barcode': location.barcode or '',
                        'usage': location.usage,
                    }
                }
                
            except Exception as e:
                _logger.error(f"Location validation error: {str(e)}")
                return {
                    'success': False,
                    'error': 'Location validation failed'
                }
                
        except Exception as e:
            _logger.error(f"Validate rack location error: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid request'
            }

    @http.route('/api/v1/mobile/rack-in/validate-product', type='json', auth='none', methods=['POST'], csrf=False)
    def validate_product(self, source_location_id=None, product_identifier=None, **kwargs):
        """
        Validate Product & Get Staging Info API
        
        Validates if a product exists and is available in the staging location
        
        Request:
        {
            "source_location_id": <staging_location_id>,
            "product_identifier": "<barcode_or_sku>"
        }
        
        Response on Success:
        {
            "success": true,
            "product": {
                "id": <product_id>,
                "name": "<product_name>",
                "display_name": "<display_name>",
                "default_code": "<product_sku>",
                "barcode": "<product_barcode>",
                "image_base64": "<base64_encoded_image>",
                "staging_qty": <available_quantity>,
                "uom_name": "<unit_of_measure>"
            }
        }
        
        Response on Failure:
        {
            "success": false,
            "error": "Product not found" | "Product not available in staging location" | "Session expired"
        }
        """
        try:
            
            # Use database from session (set during login)
            if not request.session.db:
                _logger.warning("Validate product failed: No database in session")
                return {
                    'success': False,
                    'error': 'Session expired. Please login again.'
                }
            
            # Validate inputs
            if not source_location_id:
                _logger.warning("Validate product failed: Source location ID not provided")
                return {
                    'success': False,
                    'error': 'Source location required'
                }
            
            if not product_identifier:
                _logger.warning("Validate product failed: Product identifier not provided")
                return {
                    'success': False,
                    'error': 'Product identifier required'
                }
            
            try:
                env = request.env(user=1)  # Use admin user for search
                
                # Search product by barcode first, then by default_code (SKU)
                product = env['product.product'].sudo().search([
                    '|',
                    ('barcode', '=', product_identifier),
                    ('default_code', '=', product_identifier),
                    ('active', '=', True)
                ], limit=1)
                
                if not product:
                    _logger.warning(f"Validate product failed: Product '{product_identifier}' not found")
                    return {
                        'success': False,
                        'error': 'Product not found'
                    }
                
                # Check stock availability in source location
                quant = env['stock.quant'].sudo().search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', source_location_id),
                    ('quantity', '>', 0)
                ], limit=1)
                
                if not quant:
                    _logger.warning(f"Validate product failed: Product '{product.display_name}' not available in staging location")
                    return {
                        'success': False,
                        'error': 'Product not available in staging location'
                    }
                
                # Success! Return product details
                # Get base64 image from database
                image_base64 = ''
                if product.image_128:
                    try:
                        # image_128 is already in base64 format in Odoo
                        image_base64 = product.image_128.decode('utf-8') if isinstance(product.image_128, bytes) else product.image_128
                    except Exception as img_error:
                        _logger.warning(f"Failed to get image for product {product.id}: {str(img_error)}")
                        image_base64 = ''
                
                _logger.info(f"Product validated: {product.display_name} (ID: {product.id}, Staging Qty: {quant.quantity})")
                
                return {
                    'success': True,
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'display_name': product.display_name,
                        'default_code': product.default_code or '',
                        'barcode': product.barcode or '',
                        'image_base64': image_base64,  # Base64 encoded image
                        'staging_qty': quant.quantity,
                        'uom_name': product.uom_id.name
                    }
                }
                
            except Exception as e:
                _logger.error(f"Product validation error: {str(e)}")
                return {
                    'success': False,
                    'error': 'Product validation failed'
                }
                
        except Exception as e:
            _logger.error(f"Validate product error: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid request'
            }

    @http.route('/api/v1/mobile/rack-in/submit', type='json', auth='none', methods=['POST'], csrf=False)
    def submit_rack_in(self, user_id=None, source_location_id=None, rack_location_id=None, operation_source='app', products=None, **kwargs):
        """
        Submit Rack-In Operation API
        
        Creates a rack-in log with products and quantities
        
        Request:
        {
            "user_id": <user_id_from_login>,
            "source_location_id": <staging_location_id>,
            "rack_location_id": <destination_rack_location_id>,
            "operation_source": "app",
            "products": [
                {
                    "product_id": <product_id>,
                    "staging_qty": <available_qty>,
                    "put_qty": <quantity_to_put>
                }
            ]
        }
        
        Response on Success:
        {
            "success": true,
            "rack_in_id": <rack_in_operation_id>,
            "reference": "<rack_in_reference_number>",
            "status": "normal",
            "message": "Rack-In operation created successfully"
        }
        
        Response on Failure:
        {
            "success": false,
            "error": "User not found" | "Validation error message" | "Session expired"
        }
        """
        try:
            if products is None:
                products = []
            
            # Use database from session (set during login)
            if not request.session.db:
                _logger.warning("Submit rack-in failed: No database in session")
                return {
                    'success': False,
                    'error': 'Session expired. Please login again.'
                }
            
            # Validate required fields
            if not user_id:
                return {'success': False, 'error': 'User ID required'}
            if not source_location_id:
                return {'success': False, 'error': 'Source location required'}
            if not rack_location_id:
                return {'success': False, 'error': 'Rack location required'}
            if not products or len(products) == 0:
                return {'success': False, 'error': 'At least one product required'}
            
            # Validate operation source
            if operation_source not in ['web', 'app']:
                operation_source = 'app'
            
            try:
                env = request.env(user=1)  # Use admin user for operations
                
                # Verify user exists
                user_record = env['rack.in.user.management'].sudo().browse(user_id)
                if not user_record.exists():
                    _logger.warning(f"Submit rack-in failed: User ID {user_id} not found")
                    return {
                        'success': False,
                        'error': 'User not found'
                    }
                
                # Get the linked Odoo user if available, otherwise use admin
                performed_by_id = user_record.odoo_user_id.id if user_record.odoo_user_id else 1
                
                # Prepare rack-in log data
                rack_in_vals = {
                    'source_location_id': source_location_id,
                    'rack_location_id': rack_location_id,
                    'performed_by': performed_by_id,
                    'performed_by_user': user_record.id,  # Store the rack-in user
                    'operation_source': operation_source,
                }
                
                # Validate real-time staging quantities before creating rack-in log
                for product_data in products:
                    product_id = product_data.get('product_id')
                    put_qty = product_data.get('put_qty', 0.0)
                    
                    if not product_id or put_qty <= 0:
                        continue
                    
                    # Get real-time staging quantity from database
                    quant = env['stock.quant'].sudo().search([
                        ('product_id', '=', product_id),
                        ('location_id', '=', source_location_id),
                    ], limit=1)
                    
                    actual_staging_qty = quant.quantity if quant else 0.0
                    
                    # Validate: put_qty must not exceed actual staging quantity
                    if put_qty > actual_staging_qty:
                        product = env['product.product'].sudo().browse(product_id)
                        product_name = product.display_name if product.exists() else f"Product ID: {product_id}"
                        error_msg = f"Put Quantity ({put_qty}) cannot be greater than the available Staging Quantity ({actual_staging_qty}) for product [{product_name}]."
                        _logger.warning(f"Submit rack-in failed: {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg
                        }
                
                # Create rack-in log
                rack_in_log = env['rack.in.log'].sudo().create(rack_in_vals)
                
                # Create rack-in log lines with real-time staging quantities
                for product_data in products:
                    product_id = product_data.get('product_id')
                    put_qty = product_data.get('put_qty', 0.0)
                    
                    if not product_id:
                        continue
                    
                    # Get real-time staging quantity from database
                    quant = env['stock.quant'].sudo().search([
                        ('product_id', '=', product_id),
                        ('location_id', '=', source_location_id),
                    ], limit=1)
                    
                    actual_staging_qty = quant.quantity if quant else 0.0
                    
                    line_vals = {
                        'rack_in_log_id': rack_in_log.id,
                        'product_id': product_id,
                        'staging_qty': actual_staging_qty,  # Use real-time quantity from database
                        'put_qty': put_qty,
                    }
                    
                    env['rack.in.log.line'].sudo().create(line_vals)
                
                # Execute the rack-in action
                rack_in_log.action_rack_in()
                
                # Success!
                _logger.info(f"Rack-In created: {rack_in_log.rack_process} (ID: {rack_in_log.id}, Status: {rack_in_log.status})")
                
                return {
                    'success': True,
                    'rack_in_id': rack_in_log.id,
                    'reference': rack_in_log.rack_process,
                    'status': rack_in_log.status,
                    'message': 'Rack-In operation created successfully'
                }
                
            except Exception as e:
                _logger.error(f"Submit rack-in error: {str(e)}")
                return {
                    'success': False,
                    'error': str(e)
                }
                
        except Exception as e:
            _logger.error(f"Submit rack-in request error: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid request'
            }
