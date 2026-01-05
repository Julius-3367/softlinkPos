# -*- coding: utf-8 -*-
{
    'name': 'Options Pharmacy',
    'version': '1.0.1',
    'category': 'Point of Sale',
    'summary': 'Complete Point of Sale System for Options Pharmacy',
    'description': """
        Options Pharmacy Point of Sale
        ================================
        
        Features:
        ---------
        * Prescription Management & Validation
        * Drug Registration & PPB Compliance
        * Batch & Expiry Date Tracking
        * Controlled Drugs Register
        * Patient History & Records
        * Insurance Claims Integration
        * KRA eTIMS Integration with QR Codes
        * Pharmacist Verification
        * Stock Alerts for Near-Expiry Items
        * Comprehensive Reporting
        * Multi-payment Support (Cash, M-Pesa, Insurance)
        * Thermal & A4 Receipt Printing
        * Regulatory Compliance (Kenya Pharmacy and Poisons Board)
        """,
    'author': 'SoftLink Solutions',
    'website': 'https://www.softlink.co.ke',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'point_of_sale',
        'product',
        'stock',
        'sale',
        'account',
        'contacts',
    ],
    'external_dependencies': {
        'python': ['qrcode', 'requests'],
    },
    'data': [
        # Security first (but basic groups only)
        'security/pharmacy_security.xml',
        
        # Data files
        'data/product_category_data.xml',
        'data/sequence_data.xml',
        
        # Access rules (after models are loaded)
        'security/ir.model.access.csv',
        
        # Views
        'views/pharmacy_product_views.xml',
        'views/prescription_views.xml',
        'views/pos_order_views.xml',
        'views/pos_config_views.xml',
        'views/patient_views.xml',
        'views/prescriber_views.xml',
        'views/controlled_drugs_register_views.xml',
        'views/kra_etims_views.xml',
        'views/payment_method_views.xml',
        'views/pharmacy_dashboard_views.xml',
        
        # Wizards
        'wizards/expiry_alert_wizard_views.xml',
        
        # Menu
        'views/menu_views.xml',
        
        # Reports
        'reports/prescription_report.xml',
        'reports/controlled_drugs_report.xml',
        'reports/expiry_report.xml',
        'reports/sales_report.xml',
        'reports/receipt_templates.xml',
        
        # Demo data (sample products)
        # 'data/sample_products.xml',  # TODO: Fix category references
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'softlink_pos/static/src/js/**/*',
            'softlink_pos/static/src/xml/**/*',
            'softlink_pos/static/src/css/**/*',
        ],
    },
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
