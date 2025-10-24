# WB Warehouse RackIn Module

## Overview
The `wb_rack_in` module provides a comprehensive rackin workflow system for warehouse management in Odoo 17. It combines an interactive dashboard with mobile API endpoints for complete rackin operations from staging locations to rack locations.

## Version
**v17.0.1.0.0** - Production-ready release with mobile API, dashboard, and staging quantity tracking

## Features

### 📊 Dashboard & Monitoring
- Real-time KPI cards: Total Operations and Total Quantity
- Paginated operations table with server-side pagination (10/25/50/100 rows per page)
- Advanced filtering: Search (global text), Source (Web/App), Date range (From/To)
- Source badges (Web in blue, App in light blue)
- Responsive Owl component architecture

### � Mobile API Endpoints
Complete JSON-RPC API for mobile rack-in applications:

### 📱 Mobile API Endpoints
Complete JSON-RPC API for mobile rackin applications:

#### 1. **Mobile Login**
```
POST /api/v1/mobile/login
Content-Type: application/json
```
Authenticate mobile users with PIN code.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "database": "your_db",
        "pin_code": "1234"
    },
    "id": null
}
```

**Response:**
```json
{
    "jsonrpc": "2.0",
    "id": null,
    "result": {
        "success": true,
        "user_id": 2,
        "user_name": "John Doe",
        "user_type": "app_only",
        "message": "Login successful"
    }
}
```

#### 2. **Mobile Logout**
```
POST /api/v1/mobile/logout
```
Clear mobile user session.

#### 3. **Validate Rack Location**
```
POST /api/v1/mobile/rack-in/validate-location
```
Validate rack location by barcode or name before rackin.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "location_identifier": "RACK-A-01"
    },
    "id": null
}
```

**Response:**
```json
{
    "jsonrpc": "2.0",
    "id": null,
    "result": {
        "id": 123,
        "name": "Rack A-01",
        "barcode": "RACK-A-01",
        "complete_name": "WH/Stock/Rack A-01"
    }
}
```

#### 4. **Validate Product**
```
POST /api/v1/mobile/rack-in/validate-product
```
Validate product and retrieve staging quantity.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "source_location_id": 217,
        "product_identifier": "PROD-12345"
    },
    "id": null
}
```

**Response:**
```json
{
    "jsonrpc": "2.0",
    "id": null,
    "result": {
        "id": 292164,
        "name": "Blue Fabric",
        "barcode": "PROD-12345",
        "staging_qty": 25.0,
        "image_1920_url": "/web/image?model=product.product&id=292164&field=image_1920"
    }
}
```

#### 5. **Submit RackIn**
```
POST /api/v1/mobile/rack-in/submit
```
Submit rackin operation with products and create stock movements.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "user_id": 2,
        "source_location_id": 217,
        "rack_location_id": 123,
        "products": [
            {
                "product_id": 292164,
                "staging_qty": 25.0,
                "put_qty": 10.0
            }
        ]
    },
    "id": null
}
```

**Response:**
```json
{
    "jsonrpc": "2.0",
    "id": null,
    "result": {
        "rack_in_id": 456,
        "rack_process": "RI/2025/0123",
        "status": "normal",
        "performed_by": "John Doe",
        "lines": [
            {
                "product_name": "Blue Fabric",
                "put_qty": 10.0,
                "staging_qty": 25.0
            }
        ]
    }
}
```

### 🖥️ Dashboard Statistics Endpoint
```
POST /wb_rack_in/statistics
```
Returns KPIs and paginated rackin lines for the dashboard.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "offset": 0,
        "limit": 25
    },
    "id": null
}
```

**Response:**
```json
{
    "jsonrpc": "2.0",
    "id": null,
    "result": {
        "total_operations": 150,
        "total_qty": 820.55,
        "records": [
            {
                "date": "2025-10-23 14:30:00",
                "rack": "Rack A-01",
                "product": "Blue Fabric",
                "put_qty": 10.0,
                "staging_qty": 25.0,
                "source": "app",
                "performed_by": "John Doe"
            }
        ],
        "total_records": 150,
        "offset": 0,
        "limit": 25
    }
}
```

### 🏗️ Data Models

#### RackIn Log (`rack.in.log`)
**Main Record Fields:**
- `rack_process` - Unique sequence (e.g., RI/2025/0123)
- `rack_location_id` - Target rack location (Many2one to stock.location)
- `source_location_id` - Source staging location (Many2one to stock.location)
- `performed_by` - User who performed the operation (Many2one to res.users)
- `performed_by_display` - Computed display name (shows app user name or Odoo user)
- `performed_by_user` - Related Odoo user for app users
- `status` - Operation status (always 'normal' due to validation)
- `operation_source` - Source of operation ('web' or 'app')
- `date_time` - Timestamp of the operation
- `rack_in_log_line_ids` - One2many to rack.in.log.line

**Key Features:**
- Automatic sequence generation
- Unlink protection (records cannot be deleted)
- Mail tracking and activity integration
- `action_rack_in()` method creates stock.picking and moves products

#### RackIn Log Line (`rack.in.log.line`)
**Line Item Fields:**
- `rack_in_log_id` - Parent rackin log (Many2one)
- `product_id` - Product being moved (Many2one to product.product)
- `put_qty` - Quantity put into rack (Float, required)
- `staging_qty` - Total available in staging (Float, auto-computed)

**Constraints:**
- `put_qty` must be > 0
- `put_qty` cannot exceed `staging_qty`
- Auto-fills `staging_qty` when product selected (if source is staging location)

#### Stock Location Extension (`stock.location`)
**New Field:**
- `is_staging_location` (Boolean) - Marks location as a staging area

**Purpose:** 
- Identifies staging locations for quantity calculations
- Used in product validation to compute available staging quantity

### 👥 User Management (`rack.in.user.management`)
**User Types:**
- `app_only` - Mobile app users with PIN authentication
- `odoo_linked` - Users linked to Odoo res.users

**Fields:**
- `name` - User display name
- `user_type` - Type of user (app_only / odoo_linked)
- `pin_code_number` - 4-digit PIN for mobile login
- `user_id` - Link to Odoo user (for odoo_linked type)
- `active` - Active status

**Security:**
- PIN-based authentication for mobile apps
- Separate access from Odoo users
- Can be disabled without affecting Odoo users
 

## Key Features & Enhancements

### ✨ Staging Quantity Tracking
- **Auto-Computation:** When selecting a product in a staging location, `staging_qty` is automatically calculated
- **Real-Time Validation:** Mobile API returns current staging quantity with product details
- **Smart Calculation:** Sums quantities from all staging locations (`is_staging_location = True`)
- **Constraint Enforcement:** Cannot put more than available staging quantity

### 🔒 Data Integrity
- **Unlink Protection:** RackIn logs cannot be deleted (only archived/cancelled if needed)
- **Quantity Constraints:**
  - Put quantity must be greater than 0
  - Put quantity cannot exceed staging quantity
- **Automatic Status:** All validated operations are marked as 'normal'

### 🎯 Flexible Location Search
The validate-location API supports multiple search strategies:
1. Search by exact barcode match
2. Search by location name (case-insensitive)
3. Search by complete name pattern
4. Prioritizes internal locations

### 📱 Mobile-First Design
- **PIN Authentication:** Simple 4-digit PIN for mobile app users
- **Product Images:** Base64-encoded images returned in validation API
- **Performed By Display:** Shows actual user name (not "OdooBot") for app users
- **Source Tracking:** Distinguishes between web and app operations

### 📊 Dashboard Features
- **Server-Side Pagination:** Efficient loading of large datasets
- **Client-Side Filtering:** Fast filtering on current page slice
- **Multiple Filters:** Search text, source type, date range
- **Total Quantity KPI:** Robust computation via read_group with fallback
- **Order by ID Descending:** Newest operations appear first

## Installation & Configuration

### Dependencies
- `base` - Core Odoo functionality
- `web` - Web interface and Owl framework
- `stock` - Inventory management
- `purchase` - Purchase order integration
- `mail` - Mail tracking and activities

### Setup Steps

1. **Install the Module**
   - Navigate to Apps in Odoo
   - Search for "Warehouse RackIn Workflow with API"
   - Click Install

2. **Configure Staging Locations**
   ```
   Inventory → Configuration → Locations
   - Select your staging locations
   - Enable "Is Staging Location" checkbox
   - Save
   ```

3. **Set Up Mobile Users** (Optional for mobile app)
   ```
   Inventory → Configuration → RackIn User Management
   - Create user
   - Set User Type: "App Only"
   - Assign 4-digit PIN
   - Save
   ```

4. **Access Dashboard**
   ```
   Inventory → RackIn → Dashboard
   ```

### Security & Access Rights
The module provides two access levels:
- **RackIn Manager** - Full access (create, edit, delete access rules)
- **RackIn User** - Standard access (create and view operations)

Assign groups via: Settings → Users & Companies → Users
 

## API Usage & Integration

### Authentication
Mobile API endpoints use PIN-based authentication:
1. Call `/api/v1/mobile/login` with database and PIN
2. Session cookie is set automatically
3. Use session for subsequent API calls
4. Call `/api/v1/mobile/logout` when done

Dashboard endpoint requires standard Odoo user authentication.

### Error Handling
All API endpoints return structured JSON-RPC responses:

**Success Response:**
```json
{
    "jsonrpc": "2.0",
    "id": null,
    "result": { /* response data */ }
}
```

**Error Response:**
```json
{
    "jsonrpc": "2.0",
    "id": null,
    "error": {
        "code": 200,
        "message": "Odoo Server Error",
        "data": {
            "name": "ValidationError",
            "message": "Product quantity cannot exceed staging quantity",
            "debug": "..."
        }
    }
}
```

**Common Error Scenarios:**
- `Invalid PIN Code` - Authentication failed
- `Product not found` - Invalid product identifier
- `Rack location not found` - Invalid location identifier
- `Product quantity cannot exceed staging quantity` - Validation constraint
- `Put quantity must be greater than 0` - Validation constraint

### Integration Example (Python)

```python
import requests

BASE_URL = "http://your-odoo-instance.com"
session = requests.Session()

# 1. Login
login_response = session.post(
    f"{BASE_URL}/api/v1/mobile/login",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "database": "production_db",
            "pin_code": "1234"
        },
        "id": None
    }
)

# 2. Validate Location
location_response = session.post(
    f"{BASE_URL}/api/v1/mobile/rack-in/validate-location",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"location_identifier": "RACK-A-01"},
        "id": None
    }
)

# 3. Validate Product
product_response = session.post(
    f"{BASE_URL}/api/v1/mobile/rack-in/validate-product",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "source_location_id": 217,
            "product_identifier": "PROD-12345"
        },
        "id": None
    }
)

# 4. Submit RackIn
submit_response = session.post(
    f"{BASE_URL}/api/v1/mobile/rack-in/submit",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "user_id": 2,
            "source_location_id": 217,
            "rack_location_id": 123,
            "products": [
                {
                    "product_id": 292164,
                    "staging_qty": 25.0,
                    "put_qty": 10.0
                }
            ]
        },
        "id": None
    }
)

# 5. Logout
logout_response = session.post(
    f"{BASE_URL}/api/v1/mobile/logout",
    json={"jsonrpc": "2.0", "method": "call", "params": {}, "id": None}
)
```

 

## Troubleshooting

### Common Issues

#### 1. "Invalid PIN Code" on Mobile Login
**Symptoms:** Mobile login fails with invalid PIN error

**Causes:**
- PIN not set or incorrect
- User is inactive
- Database name mismatch

**Solutions:**
1. Verify user exists in Rack-In User Management
2. Check PIN is exactly 4 digits
3. Ensure user is active (Active checkbox checked)
4. Verify correct database name in login request

#### 2. "Product not found" Error
**Symptoms:** Product validation fails

**Causes:**
- Product barcode doesn't exist
- Product archived/inactive
- Typo in product identifier

**Solutions:**
1. Check product barcode in Products menu
2. Ensure product is active
3. Try searching by product code or name
4. Verify product has a barcode set

#### 3. "Rack location not found" Error
**Symptoms:** Location validation fails

**Causes:**
- Location doesn't exist
- Location is not internal type
- Barcode mismatch

**Solutions:**
1. Verify location exists in Inventory → Configuration → Locations
2. Check location Usage is "Internal Location"
3. Verify barcode matches exactly
4. Try using location name instead of barcode

#### 4. "Product quantity cannot exceed staging quantity"
**Symptoms:** Submit fails with quantity validation error

**Causes:**
- Trying to put more than available in staging
- Staging quantity not updated
- Wrong source location

**Solutions:**
1. Check actual stock in staging location
2. Refresh product validation to get current staging_qty
3. Verify source_location_id is correct
4. Ensure put_qty ≤ staging_qty

#### 5. Dashboard Shows 0 Records
**Symptoms:** Dashboard loads but table is empty

**Causes:**
- No rack-in operations created yet
- Date filters too restrictive
- User doesn't have access rights

**Solutions:**
1. Create a test rackin operation
2. Reset filters (click Reset button)
3. Check user has RackIn User or Manager group
4. Verify user has access to the locations

#### 6. Total Quantity Shows 0
**Symptoms:** Total Quantity KPI is 0 despite operations existing

**Causes:**
- Lines have 0 put_qty values
- Database aggregation issue

**Solutions:**
1. Check rackin lines have valid put_qty > 0
2. Upgrade the module to refresh computed fields
3. Check odoo logs for any read_group errors

### Debug Tips

**Enable Developer Mode:**
Settings → Activate Developer Mode → Developer Mode

**Check Server Logs:**
Monitor your Odoo logs for detailed error messages:
```bash
tail -f /var/log/odoo/odoo-server.log
```

**Verify API Endpoint Availability:**
```bash
curl -X POST http://localhost:8070/api/v1/mobile/login \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"database":"test","pin_code":"1234"},"id":null}'
```

**Check Database Connection:**
Ensure your database credentials and connection are correct in the Odoo configuration file.

**Test Location Configuration:**
```sql
-- Run in psql to check staging locations
SELECT id, name, barcode, is_staging_location 
FROM stock_location 
WHERE usage = 'internal' 
ORDER BY name;
```

## Technical Architecture

### Backend Components

**Controllers:**
- `dashboard.py` - Dashboard statistics endpoint and legacy helper routes
- `mobile_api.py` - Complete mobile JSON-RPC API (login, logout, validate, submit)

**Models:**
- `rack_in_log.py` - Main rackin log with action_rack_in() for stock movements
- `rack_in_log_line.py` - Line items with constraints and auto-computation
- `rack_in_user_management.py` - Mobile user authentication and management
- `stock_location_inherit.py` - Extends stock.location with is_staging_location field

**Views:**
- `rack_in_log_views.xml` - Tree and form views for rackin operations
- `rack_in_user_management.xml` - User management interface
- `stock_location_view_inherit.xml` - Location configuration
- `rack_in_dashboard_template.xml` - Dashboard menu entry

**Data:**
- `rack_in_sequence.xml` - Sequence for RI/YYYY/#### numbering

**Security:**
- `ir.model.access.csv` - Access rights for Manager and User groups

### Frontend Components (Owl Framework)

**JavaScript:**
- `static/src/rack_in_list_dashboard.js` - Owl component with:
  - State management (records, pagination, filters)
  - fetchPage() - Server-side paginated data fetch
  - applyCombinedFilter() - Client-side filtering
  - Pagination controls (page size, next/prev, go to page)

**Template:**
- `static/src/dashboard_template.xml` - Owl template with:
  - KPI cards (Total Operations, Total Quantity)
  - Filter controls (Search, Source, Date From/To)
  - Paginated table (Product, Quantity, Rack, Performed By, Date, Source)
  - Source badges with color coding

### Stock Movement Flow

When `action_rack_in()` is called:
1. Creates `stock.picking` record (internal transfer)
2. For each line, creates `stock.move` from source to rack location
3. Validates the picking (auto-confirms the transfer)
4. Updates stock quantities in real-time
5. Sets status to 'normal'

### Staging Quantity Computation

When a product is selected in a staging location:
```python
# Pseudo-code
staging_locations = env['stock.location'].search([('is_staging_location', '=', True)])
quants = env['stock.quant'].search([
    ('product_id', '=', product.id),
    ('location_id', 'in', staging_locations.ids)
])
staging_qty = sum(quants.mapped('quantity'))
```

### Dashboard Pagination Strategy

**Server-Side:**
- Fetch subset of records with offset/limit
- Compute total_records count separately
- Order by id desc for newest first

**Client-Side:**
- Filter records on current page slice only
- Search applies across all visible columns
- Date range filters records within page

This hybrid approach balances performance with UX (fast filters without re-fetching).

## Best Practices

### For Developers

**Extending the Module:**
1. Inherit models using proper Odoo inheritance patterns
2. Add new API endpoints in separate controller files
3. Update `__manifest__.py` data list for new XML files
4. Follow JSON-RPC standard for API responses
5. Add computed fields with `@api.depends` decorators
6. Use `sudo()` carefully - only when necessary for cross-user access

**Code Quality:**
- Add docstrings to all methods
- Use proper logging (`_logger.info`, `_logger.exception`)
- Handle exceptions gracefully with meaningful messages
- Validate input parameters before processing
- Use `ensure_one()` for single-record operations

### For Administrators

**Performance Optimization:**
- Create database indexes on frequently searched fields (barcode, date_time)
- Archive old rackin logs instead of deleting
- Set reasonable pagination limits (25-50 records)
- Use date filters to limit dashboard data ranges

**Security:**
- Assign minimal required access rights to users
- Use different PINs for each mobile user
- Regularly audit rackin operations
- Enable audit trail in production (built into Odoo)

**Data Integrity:**
- Regular database backups
- Monitor staging quantities vs. actual stock
- Reconcile rackin operations with stock reports
- Set up automated reports for discrepancies (if needed)

## Module Metadata

- **Name:** Warehouse RackIn Workflow with API
- **Version:** 17.0.1.0.0
- **Category:** Inventory/Inventory
- **License:** LGPL-3
- **Author:** Wan Buffer Services
- **Depends:** base, web, stock, purchase, mail
- **Auto Install:** No
- **Application:** Yes

## Support & Documentation

For issues or feature requests:
1. Check this README first
2. Review the Troubleshooting section
3. Enable developer mode and check server logs
4. Contact your system administrator or development team

---

**Last Updated:** October 24, 2025  
**Module Version:** 17.0.1.0.0  
**Odoo Version:** 17.0  
**Production Status:** ✅ Ready
