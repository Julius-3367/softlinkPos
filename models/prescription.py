# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class Prescription(models.Model):
    _name = 'pharmacy.prescription'
    _description = 'Medical Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prescription_date desc, id desc'

    name = fields.Char(string='Prescription Number', required=True, copy=False, readonly=True, 
                       default='New', tracking=True)
    
    # Patient and Prescriber
    patient_id = fields.Many2one('pharmacy.patient', string='Patient', required=True, tracking=True)
    patient_age = fields.Integer(string='Patient Age', related='patient_id.age', readonly=True)
    patient_phone = fields.Char(string='Patient Phone', related='patient_id.phone', readonly=True)
    
    prescriber_id = fields.Many2one('pharmacy.prescriber', string='Prescriber', required=True, tracking=True)
    prescriber_license = fields.Char(string='License No.', related='prescriber_id.license_number', readonly=True)
    
    # Prescription Details
    prescription_date = fields.Date(string='Prescription Date', required=True, default=fields.Date.today, tracking=True)
    valid_until = fields.Date(string='Valid Until', compute='_compute_valid_until', store=True,
                              help='Prescription validity period (usually 6 months)')
    is_valid = fields.Boolean(string='Is Valid', compute='_compute_is_valid', store=True)
    
    # Prescription Lines
    line_ids = fields.One2many('pharmacy.prescription.line', 'prescription_id', string='Prescription Lines')
    
    # Diagnosis
    diagnosis = fields.Text(string='Diagnosis', required=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('partially_dispensed', 'Partially Dispensed'),
        ('dispensed', 'Fully Dispensed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Dispensing Information
    dispensed_by = fields.Many2one('res.users', string='Dispensed By', readonly=True)
    dispensing_date = fields.Datetime(string='Dispensing Date', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='POS Order', readonly=True)
    
    # Verification
    verified_by_pharmacist = fields.Boolean(string='Verified by Pharmacist', default=False, tracking=True)
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist', readonly=True)
    verification_date = fields.Datetime(string='Verification Date', readonly=True)
    pharmacist_notes = fields.Text(string='Pharmacist Notes')
    
    # Additional Information
    special_instructions = fields.Text(string='Special Instructions')
    notes = fields.Text(string='Internal Notes')
    
    # Attachments (scanned prescription)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',
                                       help='Upload scanned copy of prescription')
    
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                 default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    @api.depends('prescription_date')
    def _compute_valid_until(self):
        for record in self:
            if record.prescription_date:
                # Standard prescription validity: 6 months
                record.valid_until = record.prescription_date + timedelta(days=180)
            else:
                record.valid_until = False
    
    @api.depends('valid_until', 'state')
    def _compute_is_valid(self):
        today = fields.Date.today()
        for record in self:
            if record.state == 'cancelled':
                record.is_valid = False
            elif record.valid_until:
                record.is_valid = record.valid_until >= today
            else:
                record.is_valid = False
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('pharmacy.prescription') or 'New'
        return super(Prescription, self).create(vals)
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})
    
    def action_verify_prescription(self):
        """Pharmacist verification of prescription"""
        if not self.env.user.has_group('softlink_pos.group_pharmacy_pharmacist'):
            raise UserError('Only pharmacists can verify prescriptions.')
        
        self.write({
            'verified_by_pharmacist': True,
            'pharmacist_id': self.env.user.id,
            'verification_date': fields.Datetime.now(),
        })
    
    def action_dispense(self):
        """Mark prescription as dispensed"""
        self.write({
            'state': 'dispensed',
            'dispensed_by': self.env.user.id,
            'dispensing_date': fields.Datetime.now(),
        })
    
    def action_cancel(self):
        if self.state == 'dispensed':
            raise UserError('Cannot cancel a dispensed prescription.')
        self.write({'state': 'cancelled'})
    
    def action_set_to_draft(self):
        self.write({'state': 'draft'})
    
    @api.constrains('valid_until')
    def _check_validity(self):
        for record in self:
            if record.valid_until and record.valid_until < record.prescription_date:
                raise ValidationError('Valid until date cannot be before prescription date.')
    
    def check_prescription_validity(self):
        """Check if prescription is valid for dispensing"""
        self.ensure_one()
        if not self.is_valid:
            raise ValidationError(f'Prescription {self.name} has expired and cannot be dispensed.')
        if self.state == 'cancelled':
            raise ValidationError(f'Prescription {self.name} has been cancelled.')
        if not self.verified_by_pharmacist:
            raise ValidationError(f'Prescription {self.name} must be verified by a pharmacist before dispensing.')
        return True


class PrescriptionLine(models.Model):
    _name = 'pharmacy.prescription.line'
    _description = 'Prescription Line'

    prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription', required=True, ondelete='cascade')
    
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                  domain="[('is_pharmaceutical', '=', True)]")
    pharmacy_product_id = fields.Many2one('pharmacy.product', string='Pharmacy Product', 
                                          related='product_id.product_tmpl_id.pharmacy_product_id', readonly=True)
    
    # Dosage Instructions
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True)
    
    dosage = fields.Char(string='Dosage', help='e.g., 1 tablet, 5ml')
    frequency = fields.Char(string='Frequency', help='e.g., Twice daily, Every 8 hours')
    duration = fields.Char(string='Duration', help='e.g., 7 days, 2 weeks')
    
    instructions = fields.Text(string='Instructions', help='e.g., Take with food, Before meals')
    
    # Dispensing tracking
    quantity_dispensed = fields.Float(string='Quantity Dispensed', default=0.0, readonly=True)
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining', store=True)
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('partially_dispensed', 'Partially Dispensed'),
        ('dispensed', 'Dispensed'),
    ], string='Status', default='pending', compute='_compute_state', store=True)
    
    @api.depends('quantity', 'quantity_dispensed')
    def _compute_remaining(self):
        for record in self:
            record.remaining_quantity = record.quantity - record.quantity_dispensed
    
    @api.depends('quantity', 'quantity_dispensed')
    def _compute_state(self):
        for record in self:
            if record.quantity_dispensed == 0:
                record.state = 'pending'
            elif record.quantity_dispensed >= record.quantity:
                record.state = 'dispensed'
            else:
                record.state = 'partially_dispensed'
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError('Quantity must be greater than zero.')
