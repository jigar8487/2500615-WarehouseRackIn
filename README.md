# Warehouse RackIn Management System

A comprehensive Odoo 18 module providing complete warehouse rack-in workflow management with mobile API integration and web dashboard for inventory operations.

## 🎯 Project Overview

This project contains the **WB Warehouse RackIn** module (`wb_rack_in`) - a production-ready Odoo addon that streamlines warehouse rack-in operations from staging locations to final rack positions. The module combines web-based management with mobile API endpoints for seamless integration with warehouse management applications.

## 📋 Module Information

- **Module Name:** `wb_rack_in`
- **Version:** 18.0.1.0.0
- **Category:** Inventory/Inventory
- **License:** LGPL-3
- **Author:** Wan Buffer Services
- **Odoo Version:** 18.0+

## 🚀 Key Features

### 📱 Mobile API Integration
- **PIN-based authentication** for mobile app users
- **Complete JSON-RPC API** for rack-in operations
- **Real-time inventory validation** and quantity tracking
- **Barcode scanning support** for products and locations

### 🖥️ Web Dashboard
- **Real-time KPIs** (Total Operations, Total Quantity)
- **Advanced filtering** (Search, Source, Date range)
- **Server-side pagination** for performance
- **OWL component** architecture for Odoo 18

### 📊 Inventory Management
- **Staging location management** with quantity tracking
- **Stock movement automation** via stock.picking
- **Complete traceability** and audit logging
- **Role-based access control** for users

## 🏗️ Module Structure

```
wb_rack_in/
├── __init__.py                     # Module initialization
├── __manifest__.py                 # Module manifest and dependencies
├── hooks.py                        # Post-install/update hooks
├── README.md                       # Detailed module documentation
├── controllers/                    # HTTP controllers
│   ├── __init__.py
│   ├── dashboard.py               # Dashboard statistics and API endpoints
│   └── mobile_api.py              # Mobile JSON-RPC API endpoints
├── data/                          # Data files
│   ├── rack_in_sequence.xml       # Sequence for rack-in numbering
│   └── cleanup_odoo_users.xml.disabled
├── models/                        # Data models
│   ├── __init__.py
│   ├── rack_in_log.py             # Main rack-in log model
│   ├── rack_in_log_line.py        # Rack-in line items
│   ├── rack_in_user_management.py # Mobile user management
│   └── stock_location_inherit.py  # Location extensions
├── security/                      # Access rights
│   └── ir.model.access.csv        # Model access permissions
├── static/src/                    # Frontend assets
│   ├── dashboard_template.xml     # OWL template for dashboard
│   ├── rack_in_list_dashboard.js  # Dashboard component (OWL)
│   └── rack_in_dashboard_loader.js # Client action registration
└── views/                         # XML views
    ├── rack_in_dashboard_template.xml    # Dashboard menu
    ├── rack_in_log_views.xml            # Log views
    ├── rack_in_user_management.xml      # User management
    └── stock_location_view_inherit.xml  # Location views
```

## 📦 Dependencies

The module requires the following Odoo modules:
- `base` - Core Odoo functionality
- `web` - Web interface and OWL framework
- `stock` - Inventory management
- `purchase` - Purchase order integration
- `mail` - Mail tracking and activities

## 🔧 Installation

1. **Copy Module**
   ```bash
   cp -r wb_rack_in /path/to/odoo/addons/
   ```

2. **Update App List**
   - Navigate to Apps in Odoo
   - Click "Update Apps List"

3. **Install Module**
   - Search for "Warehouse RackIn"
   - Click Install

4. **Configure Access Rights**
   - Assign users to "RackIn User" or "RackIn Manager" groups
   - Settings → Users & Companies → Users

## 🌐 API Endpoints

The module provides comprehensive REST API endpoints for mobile integration:

### Authentication
- `POST /api/v1/mobile/login` - User authentication with PIN
- `POST /api/v1/mobile/logout` - Session logout

### Rack-In Operations
- `POST /api/v1/mobile/rack-in/validate-location` - Validate rack location
- `POST /api/v1/mobile/rack-in/validate-product` - Validate product and get staging qty
- `POST /api/v1/mobile/rack-in/submit` - Submit rack-in operation

### Dashboard
- `POST /wb_rack_in/statistics` - Dashboard statistics and data

## 📋 Data Models

### Core Models
- **`rack.in.log`** - Main rack-in operations with sequence numbering
- **`rack.in.log.line`** - Individual line items with product quantities
- **`rack.in.user.management`** - Mobile user authentication and roles
- **`stock.location`** - Extended with staging location functionality

## 💡 Usage Examples

### Mobile API Integration
```python
# Login
response = requests.post('/api/v1/mobile/login', json={
    "database": "production_db",
    "pin_code": "1234"
})

# Validate Product
response = requests.post('/api/v1/mobile/rack-in/validate-product', json={
    "source_location_id": 217,
    "product_identifier": "PROD-12345"
})

# Submit Rack-In
response = requests.post('/api/v1/mobile/rack-in/submit', json={
    "user_id": 2,
    "source_location_id": 217,
    "rack_location_id": 123,
    "products": [{"product_id": 292164, "staging_qty": 25.0, "put_qty": 10.0}]
})
```

## 🔐 Security Features

- **PIN-based mobile authentication** (4-digit codes)
- **Role-based access control** (Manager/User groups)
- **Audit logging** with mail tracking
- **Data validation** and constraint enforcement
- **Unlink protection** for completed operations

## 📈 Performance Features

- **Server-side pagination** for large datasets
- **Optimized database queries** with proper indexing
- **Client-side filtering** for fast UX
- **Background stock movement** processing
- **Efficient staging quantity** calculations

## 🛠️ Development

### Testing
Run the module with developer mode enabled to access debugging tools:
```bash
odoo-bin -d database_name --dev=all
```

### Customization
The module follows Odoo best practices for inheritance and extension:
- Models can be inherited using standard Odoo patterns
- API endpoints can be extended in separate controller files
- Views can be inherited and customized
- Security rules can be modified via ir.model.access.csv

## 📚 Documentation

For detailed documentation including API specifications, troubleshooting, and configuration guides, see the module's internal README at `wb_rack_in/README.md`.

## 🤝 Contributing

This is a production module developed by Wan Buffer Services. For issues or feature requests, contact the development team.

## 📄 License

This project is licensed under LGPL-3 - see the module manifest for details.

---

**Last Updated:** October 27, 2025  
**Project Status:** ✅ Production Ready  
**Module Version:** 18.0.1.0.0
