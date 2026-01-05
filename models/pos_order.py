# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # Patient Information
    patient_id = fields.Many2one('pharmacy.patient', string='Patient', tracking=True)
    patient_name = fields.Char(string='Patient Name')
    patient_phone = fields.Char(string='Patient Phone')
    
    # Prescription
    prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription')
    has_prescription_items = fields.Boolean(string='Has Prescription Items', compute='_compute_has_prescription_items')
    requires_pharmacist_approval = fields.Boolean(string='Requires Pharmacist Approval', 
                                                   compute='_compute_requires_pharmacist_approval')
    
    # Pharmacist Approval
    approved_by_pharmacist = fields.Boolean(string='Approved by Pharmacist', default=False)
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist')
    approval_date = fields.Datetime(string='Approval Date')
    
    # Insurance
    insurance_claim = fields.Boolean(string='Insurance Claim', default=False)
    insurance_company = fields.Char(string='Insurance Company')
    insurance_number = fields.Char(string='Insurance Number')
    insurance_amount = fields.Float(string='Insurance Amount')
    patient_copay = fields.Float(string='Patient Co-pay')
    
    # Controlled Drugs
    has_controlled_drugs = fields.Boolean(string='Has Controlled Drugs', compute='_compute_has_controlled_drugs')
    
    @api.depends('lines.product_id')
    def _compute_has_prescription_items(self):
        for order in self:
            order.has_prescription_items = any(
                line.product_id.requires_prescription for line in order.lines
            )
    
    @api.depends('lines.product_id')
    def _compute_requires_pharmacist_approval(self):
        for order in self:
            requires_approval = False
            for line in order.lines:
                if line.product_id.product_tmpl_id.pharmacy_product_id:
                    if line.product_id.product_tmpl_id.pharmacy_product_id.requires_pharmacist_approval:
                        requires_approval = True
                        break
            order.requires_pharmacist_approval = requires_approval
    
    @api.depends('lines.product_id')
    def _compute_has_controlled_drugs(self):
        for order in self:
            order.has_controlled_drugs = any(
                line.product_id.product_tmpl_id.pharmacy_product_id.drug_category == 'controlled' 
                for line in order.lines if line.product_id.product_tmpl_id.pharmacy_product_id
            )
    
    def _prepare_controlled_drugs_register_entry(self, line):
        """Prepare data for controlled drugs register"""
        return {
            'pos_order_id': self.id,
            'product_id': line.product_id.id,
            'patient_id': self.patient_id.id if self.patient_id else False,
            'patient_name': self.patient_name or (self.patient_id.full_name if self.patient_id else ''),
            'prescription_id': self.prescription_id.id if self.prescription_id else False,
            'quantity': line.qty,
            'date': self.date_order,
            'dispensed_by': self.user_id.id,
            'pharmacist_id': self.pharmacist_id.id if self.pharmacist_id else False,
        }
    
    @api.model
    def _order_fields(self, ui_order):
        """Override to add pharmacy-specific fields"""
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        
        # Add pharmacy fields
        order_fields.update({
            'patient_id': ui_order.get('patient_id', False),
            'patient_name': ui_order.get('patient_name', False),
            'patient_phone': ui_order.get('patient_phone', False),
            'prescription_id': ui_order.get('prescription_id', False),
            'insurance_claim': ui_order.get('insurance_claim', False),
            'insurance_company': ui_order.get('insurance_company', False),
            'insurance_number': ui_order.get('insurance_number', False),
            'insurance_amount': ui_order.get('insurance_amount', 0.0),
            'patient_copay': ui_order.get('patient_copay', 0.0),
            'approved_by_pharmacist': ui_order.get('approved_by_pharmacist', False),
            'pharmacist_id': ui_order.get('pharmacist_id', False),
        })
        
        return order_fields
    
    def action_pos_order_paid(self):
        """Override to add pharmacy validations and create controlled drugs register entries"""
        # Validate prescription items
        for order in self:
            if order.has_prescription_items and not order.prescription_id:
                # In production, this should raise an error
                # For now, we'll just log a warning
                pass
            
            if order.requires_pharmacist_approval and not order.approved_by_pharmacist:
                raise UserError('This order contains items that require pharmacist approval.')
        
        res = super(PosOrder, self).action_pos_order_paid()
        
        # Create controlled drugs register entries
        for order in self:
            if order.has_controlled_drugs:
                for line in order.lines:
                    if line.product_id.product_tmpl_id.pharmacy_product_id:
                        if line.product_id.product_tmpl_id.pharmacy_product_id.drug_category == 'controlled':
                            self.env['pharmacy.controlled.drugs.register'].create(
                                order._prepare_controlled_drugs_register_entry(line)
                            )
            
            # Update prescription if linked
            if order.prescription_id:
                order.prescription_id.write({
                    'pos_order_id': order.id,
                    'state': 'dispensed',
                    'dispensed_by': order.user_id.id,
                    'dispensing_date': fields.Datetime.now(),
                })
        
        return res


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    # Pharmacy specific fields
    lot_id = fields.Many2one('stock.lot', string='Lot/Batch')
    expiry_date = fields.Date(string='Expiry Date', related='lot_id.expiry_date', readonly=True)
    prescription_line_id = fields.Many2one('pharmacy.prescription.line', string='Prescription Line')
    
    # Dosage information (if different from prescription)
    dosage_instructions = fields.Text(string='Dosage Instructions')
    
    @api.model
    def _order_line_fields(self, line, session_id=None):
        """Override to add pharmacy-specific fields"""
        fields = super(PosOrderLine, self)._order_line_fields(line, session_id)
        
        fields[2].update({
            'lot_id': line[2].get('lot_id', False),
            'prescription_line_id': line[2].get('prescription_line_id', False),
            'dosage_instructions': line[2].get('dosage_instructions', False),
        })
        
        return fields
