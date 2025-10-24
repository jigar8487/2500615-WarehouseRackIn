from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
import logging
import json

_logger = logging.getLogger(__name__)

class AwesomeDashboard(http.Controller):
    @http.route('/wb_rack_in/statistics', type='json', auth='user')
    def get_statistics(self, offset=0, limit=25):
        """
        Return dashboard KPIs and a paginated slice of rack-in lines for the table.

        Params (JSON):
        - offset: integer record offset (default 0)
        - limit: page size (default 25)
        """
        env = request.env

        # KPIs computed on rack.in.log
        RackLog = env['rack.in.log'].sudo().search([], order="date_time desc")
        total_operations = len(RackLog)

        # Sum of put_qty across all lines (efficient via read_group)
        line_model = env['rack.in.log.line'].sudo()
        # Try read_group for efficiency; if it yields no rows or unexpected payload, fallback to explicit sum
        try:
            rg = line_model.read_group([], ['put_qty:sum'], [])
            if rg and isinstance(rg, list) and rg[0].get('put_qty_sum') is not None:
                total_put_qty = rg[0].get('put_qty_sum') or 0.0
            else:
                total_put_qty = sum(line_model.search([]).mapped('put_qty')) or 0.0
        except Exception:
            total_put_qty = sum(line_model.search([]).mapped('put_qty')) or 0.0

        # Pagination params
        try:
            offset = int(offset) if offset is not None else 0
            limit = int(limit) if limit is not None else 25
        except Exception:
            offset, limit = 0, 25

        total_records = line_model.search_count([])
        # Note: ordering by a related field (rack_in_log_id.date_time) can raise ORM errors on some setups.
        # Use a safe fallback ordering by line creation/id descending, which correlates with log recency.
        lines = line_model.search([], offset=offset, limit=limit, order='id desc')

        # Build table rows (one per line)
        lines_data = []
        for line in lines:
            log = line.rack_in_log_id
            lines_data.append({
                'date': log.date_time.strftime('%Y-%m-%d %H:%M:%S') if log.date_time else '',
                'rack': log.rack_location_id.name if log.rack_location_id else 'Unknown',
                'product': line.product_id.name if line.product_id else 'Unknown',
                'put_qty': line.put_qty,
                'staging_qty': line.staging_qty,
                'source': getattr(log, 'operation_source', 'unknown'),
                'performed_by': getattr(log, 'performed_by_display', None) or (log.performed_by.name if log.performed_by else 'Unknown'),
            })

        return {
            'total_operations': total_operations,
            'total_qty': total_put_qty,
            'records': lines_data,
            'total_records': total_records,
            'offset': offset,
            'limit': limit,
        }

    # API to create Rack-In Log with lines and optional validation
    @http.route('/api/v1/rack-in', type='json', auth='user', methods=['POST'], csrf=False)
    def create_rack_in(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data) or kwargs

            # Required field validations
            required_fields = ['rack_location_id', 'source_location_id', 'operation_source', 'lines']
            for field in required_fields:
                if field not in data:
                    return {'status': 'error', 'error': {'code': 'VALIDATION_ERROR', 'message': f'Missing required field: {field}'}}

            # Line validation
            if not isinstance(data['lines'], list) or not data['lines']:
                return {'status': 'error', 'error': {'code': 'VALIDATION_ERROR', 'message': 'Line items are required and must be a list.'}}

            # Validate that the rack and source locations exist
            rack_location = request.env['stock.location'].sudo().browse(data['rack_location_id'])
            if not rack_location.exists():
                return {'status': 'error', 'error': {'code': 'VALIDATION_ERROR', 'message': f'Rack location with ID {data["rack_location_id"]} not found.'}}
            
            source_location = request.env['stock.location'].sudo().browse(data['source_location_id'])
            if not source_location.exists():
                return {'status': 'error', 'error': {'code': 'VALIDATION_ERROR', 'message': f'Source location with ID {data["source_location_id"]} not found.'}}

            # Prepare line items
            lines = []
            for line in data['lines']:
                if not all(k in line for k in ['product_id', 'put_qty']):
                    return {'status': 'error', 'error': {'code': 'VALIDATION_ERROR', 'message': 'Each line must include product_id and put_qty.'}}
                
                # Validate product exists
                product = request.env['product.product'].sudo().browse(line['product_id'])
                if not product.exists():
                    return {'status': 'error', 'error': {'code': 'VALIDATION_ERROR', 'message': f'Product with ID {line["product_id"]} not found.'}}
                
                lines.append((0, 0, {
                    'product_id': line['product_id'],
                    'put_qty': line['put_qty'],
                    'staging_qty': line.get('staging_qty', 0.0)
                }))

            # Create record
            rack_log = request.env['rack.in.log'].sudo().create({
                'rack_location_id': data['rack_location_id'],
                'source_location_id': data['source_location_id'],
                'operation_source': data.get('operation_source', 'web'),
                'rack_in_log_line_ids': lines
            })

            # Optionally perform action
            if data.get('auto_validate'):
                rack_log.action_rack_in()

            return {
                'status': 'success',
                'data': {
                    'id': rack_log.id,
                    'name': rack_log.rack_process,
                    'status': rack_log.status,
                    'performed_by': rack_log.performed_by.name,
                    'date_time': rack_log.date_time.isoformat(),
                    'lines': [{
                        'product_id': line.product_id.id,
                        'product_name': line.product_id.name,
                        'put_qty': line.put_qty,
                        'staging_qty': line.staging_qty,
                    } for line in rack_log.rack_in_log_line_ids]
                }
            }

        except ValidationError as ve:
            _logger.exception("Validation error creating rack-in entry")
            return {'status': 'error', 'error': {'code': 'VALIDATION_ERROR', 'message': str(ve)}}
        except Exception as e:
            _logger.exception("Error creating rack-in entry: %s", str(e))
            return {'status': 'error', 'error': {'code': 'SERVER_ERROR', 'message': f'Internal server error: {str(e)}'}}

    # API to get rack-in logs with filters
    @http.route('/api/v1/rack-in/logs', type='json', auth='user', methods=['GET'], csrf=False)
    def get_rack_in_logs(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data) or kwargs
            domain = []
            if data.get('rack_location_id'):
                domain.append(('rack_location_id', '=', data['rack_location_id']))
            if data.get('status'):
                domain.append(('status', '=', data['status']))
            if data.get('date_from'):
                domain.append(('date_time', '>=', data['date_from']))
            if data.get('date_to'):
                domain.append(('date_time', '<=', data['date_to']))

            limit = int(data.get('limit', 50))
            offset = int(data.get('offset', 0))

            logs = request.env['rack.in.log'].sudo().search(domain, limit=limit, offset=offset, order='date_time desc')

            total = request.env['rack.in.log'].sudo().search_count(domain)

            result = {
                'status': 'success',
                'data': {
                    'total': total,
                    'count': len(logs),
                    'logs': []
                }
            }

            for log in logs:
                log_data = {
                    'id': log.id,
                    'rack_process': log.rack_process,
                    'rack_location': log.rack_location_id.name,
                    'source_location': log.source_location_id.name,
                    'status': log.status,
                    'operation_source': log.operation_source,
                    'performed_by': log.performed_by.name,
                    'date_time': log.date_time.isoformat(),
                    'lines': []
                }
                
                for line in log.rack_in_log_line_ids:
                    log_data['lines'].append({
                        'product_id': line.product_id.id,
                        'product_name': line.product_id.name,
                        'put_qty': line.put_qty,
                        'staging_qty': line.staging_qty,
                    })
                
                result['data']['logs'].append(log_data)

            return result
        except Exception as e:
            _logger.exception("Error fetching rack-in logs")
            return {'status': 'error', 'error': {'code': 'SERVER_ERROR', 'message': 'Internal server error'}}

    # API to get product by barcode
    @http.route('/api/v1/products/barcode/<string:barcode>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_product_by_barcode(self, barcode, **kwargs):
        try:
            product = request.env['product.product'].sudo().search([('barcode', '=', barcode)], limit=1)
            if product:
                # Get staging location quantity
                staging_qty = 0.0
                staging_locations = request.env['stock.location'].sudo().search([('is_staging_location', '=', True)])
                if staging_locations:
                    # Get quantity from all staging locations for this product
                    quants = request.env['stock.quant'].sudo().search([
                        ('product_id', '=', product.id),
                        ('location_id', 'in', staging_locations.ids),
                        ('quantity', '>', 0)
                    ])
                    staging_qty = sum(quants.mapped('quantity'))

                return json.dumps({
                    'success': True,
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'barcode': product.barcode,
                        'default_code': product.default_code,
                        'categ_id': product.categ_id.name if product.categ_id else None,
                        'list_price': product.list_price,
                        'standard_price': product.standard_price,
                        'uom_name': product.uom_id.name if product.uom_id else None,
                        'qty_available': product.qty_available,
                        'virtual_available': product.virtual_available,
                        'staging_qty': staging_qty,
                        'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None
                    }
                })
            else:
                return json.dumps({
                    'success': False,
                    'message': 'Product not found'
                })
        except Exception as e:
            _logger.exception("Error fetching product by barcode")
            return json.dumps({
                'success': False,
                'message': 'Internal server error'
            })

    # API to get rack location by barcode - Updated with more flexible search
    @http.route('/api/v1/racks/barcode/<string:barcode>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_rack_by_barcode(self, barcode, **kwargs):
        try:
            # First try searching for staging locations, then any internal location with the barcode
            location = request.env['stock.location'].sudo().search([
                ('barcode', '=', barcode),
                ('is_staging_location', '=', True)
            ], limit=1)
            
            if not location:
                # If no staging location found, search for any internal location
                location = request.env['stock.location'].sudo().search([
                    ('barcode', '=', barcode),
                    ('usage', '=', 'internal')
                ], limit=1)
            
            if not location:
                # If still no location found, search by name or complete name
                location = request.env['stock.location'].sudo().search([
                    '|', ('name', 'ilike', barcode), ('complete_name', 'ilike', barcode),
                    ('usage', '=', 'internal')
                ], limit=1)

            if location:
                return json.dumps({
                    'success': True,
                    'rack': {
                        'id': location.id,
                        'name': location.name,
                        'barcode': location.barcode,
                        'complete_name': location.complete_name,
                        'usage': location.usage,
                        'is_staging_location': getattr(location, 'is_staging_location', False),
                        'company_id': location.company_id.name if location.company_id else None,
                        'warehouse_id': location.warehouse_id.name if hasattr(location, 'warehouse_id') and location.warehouse_id else None
                    }
                })
            else:
                return json.dumps({
                    'success': False,
                    'message': 'Rack location not found'
                })
        except Exception as e:
            _logger.exception("Error fetching rack location by barcode")
            return json.dumps({
                'success': False,
                'message': 'Internal server error'
            })

    # Debug endpoint to list available locations
    @http.route('/api/v1/debug/locations', type='http', auth='user', methods=['GET'], csrf=False)
    def debug_locations(self, **kwargs):
        try:
            # Get recent locations with barcodes
            locations = request.env['stock.location'].sudo().search([
                ('barcode', '!=', False),
                ('usage', '=', 'internal')
            ], limit=50, order='write_date desc')
            
            location_list = []
            for loc in locations:
                location_list.append({
                    'id': loc.id,
                    'name': loc.name,
                    'barcode': loc.barcode,
                    'complete_name': loc.complete_name,
                    'usage': loc.usage,
                    'is_staging_location': getattr(loc, 'is_staging_location', False)
                })
            
            return json.dumps({
                'success': True,
                'count': len(location_list),
                'locations': location_list
            })
        except Exception as e:
            _logger.exception("Error fetching debug locations")
            return json.dumps({
                'success': False,
                'message': 'Internal server error'
            })
