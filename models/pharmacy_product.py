# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PharmacyProduct(models.Model):
    _name = 'pharmacy.product'
    _description = 'Pharmacy Product Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Drug Name', required=True, tracking=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    
    # Drug Classification
    generic_name = fields.Char(string='Generic Name', required=True, tracking=True)
    brand_name = fields.Char(string='Brand Name', tracking=True)
    active_ingredient = fields.Text(string='Active Ingredients', required=True)
    
    # Registration Details
    ppb_registration_no = fields.Char(string='PPB Registration Number', tracking=True, 
                                       help='Kenya Pharmacy and Poisons Board Registration Number')
    registration_date = fields.Date(string='Registration Date')
    registration_expiry = fields.Date(string='Registration Expiry')
    
    # Drug Classification
    drug_category = fields.Selection([
        ('prescription', 'Prescription Only Medicine (POM)'),
        ('otc', 'Over The Counter (OTC)'),
        ('controlled', 'Controlled Drug'),
        ('pharmacy', 'Pharmacy Medicine (P)'),
        ('general', 'General Sales List (GSL)'),
    ], string='Drug Category', required=True, default='otc', tracking=True)
    
    schedule = fields.Selection([
        ('schedule_1', 'Schedule 1 - Controlled'),
        ('schedule_2', 'Schedule 2 - Restricted'),
        ('unscheduled', 'Unscheduled'),
    ], string='Drug Schedule', default='unscheduled')
    
    # Dosage Information
    dosage_form = fields.Selection([
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('suspension', 'Suspension'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('ointment', 'Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('suppository', 'Suppository'),
        ('other', 'Other'),
    ], string='Dosage Form', required=True)
    
    strength = fields.Char(string='Strength', help='e.g., 500mg, 5ml')
    pack_size = fields.Integer(string='Pack Size', default=1)
    
    # Medical Information
    indication = fields.Text(string='Indications')
    contraindication = fields.Text(string='Contraindications')
    side_effects = fields.Text(string='Side Effects')
    dosage_instructions = fields.Text(string='Dosage Instructions')
    storage_conditions = fields.Text(string='Storage Conditions')
    
    # Prescription Requirements
    requires_prescription = fields.Boolean(string='Requires Prescription', compute='_compute_requires_prescription', store=True)
    max_otc_quantity = fields.Integer(string='Max OTC Quantity', help='Maximum quantity that can be sold without prescription')
    
    # Manufacturer Details
    manufacturer_id = fields.Many2one('res.partner', string='Manufacturer', domain=[('is_company', '=', True)])
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('is_company', '=', True)])
    country_of_origin = fields.Many2one('res.country', string='Country of Origin')
    
    # Stock and Expiry
    track_expiry = fields.Boolean(string='Track Expiry Date', default=True)
    expiry_alert_days = fields.Integer(string='Expiry Alert Days', default=90, 
                                        help='Alert when product is about to expire within these many days')
    
    # Additional Info
    barcode = fields.Char(string='Barcode', related='product_id.barcode', readonly=False)
    therapeutic_class = fields.Char(string='Therapeutic Class')
    pharmacological_class = fields.Char(string='Pharmacological Class')
    
    # Compliance
    requires_pharmacist_approval = fields.Boolean(string='Requires Pharmacist Approval', 
                                                   compute='_compute_requires_pharmacist', store=True)
    cold_chain = fields.Boolean(string='Cold Chain Required', help='Requires refrigeration')
    
    @api.depends('drug_category')
    def _compute_requires_prescription(self):
        for record in self:
            record.requires_prescription = record.drug_category in ['prescription', 'controlled']
    
    @api.depends('drug_category', 'schedule')
    def _compute_requires_pharmacist(self):
        for record in self:
            record.requires_pharmacist_approval = record.drug_category in ['prescription', 'controlled'] or \
                                                   record.schedule in ['schedule_1', 'schedule_2']
    
    @api.constrains('ppb_registration_no')
    def _check_ppb_registration(self):
        for record in self:
            if record.ppb_registration_no:
                existing = self.search([
                    ('ppb_registration_no', '=', record.ppb_registration_no),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(f"PPB Registration Number {record.ppb_registration_no} already exists for {existing.name}")
    
    @api.constrains('registration_expiry')
    def _check_registration_expiry(self):
        for record in self:
            if record.registration_expiry and record.registration_expiry < fields.Date.today():
                raise ValidationError(f"Registration for {record.name} has expired. Please renew before selling.")
