# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Pharmacy Settings
    is_pharmacy_pos = fields.Boolean(string='Is Pharmacy POS', default=True,
                                      help='Enable pharmacy-specific features')
    
    require_prescription_validation = fields.Boolean(string='Require Prescription Validation', default=True,
                                                      help='Validate prescriptions before dispensing')
    
    require_pharmacist_approval = fields.Boolean(string='Require Pharmacist Approval', default=True,
                                                  help='Require pharmacist approval for prescription items')
    
    allow_otc_sales = fields.Boolean(string='Allow OTC Sales', default=True,
                                      help='Allow over-the-counter sales without prescription')
    
    block_expired_products = fields.Boolean(string='Block Expired Products', default=True,
                                            help='Prevent sale of expired products')
    
    warn_near_expiry = fields.Boolean(string='Warn Near Expiry', default=True,
                                       help='Show warning for products near expiry')
    
    near_expiry_days = fields.Integer(string='Near Expiry Days', default=90,
                                       help='Days before expiry to show warning')
    
    # Insurance Settings
    enable_insurance = fields.Boolean(string='Enable Insurance', default=True)
    default_insurance_percentage = fields.Float(string='Default Insurance Coverage %', default=80.0)
    
    # Patient Management
    require_patient_info = fields.Boolean(string='Require Patient Information', default=True,
                                          help='Require patient details for prescription sales')
    
    auto_create_patient = fields.Boolean(string='Auto Create Patient', default=True,
                                          help='Automatically create patient record if not exists')
