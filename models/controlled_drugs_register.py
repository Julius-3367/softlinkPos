# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ControlledDrugsRegister(models.Model):
    _name = 'pharmacy.controlled.drugs.register'
    _description = 'Controlled Drugs Register'
    _order = 'date desc, id desc'
    _rec_name = 'product_id'

    # Transaction Details
    date = fields.Datetime(string='Date & Time', required=True, default=fields.Datetime.now)
    
    # Product Information
    product_id = fields.Many2one('product.product', string='Product', required=True)
    pharmacy_product_id = fields.Many2one('pharmacy.product', string='Pharmacy Product',
                                          related='product_id.product_tmpl_id.pharmacy_product_id', readonly=True)
    
    # Patient Information
    patient_id = fields.Many2one('pharmacy.patient', string='Patient')
    patient_name = fields.Char(string='Patient Name', required=True)
    patient_id_number = fields.Char(string='Patient ID Number')
    patient_address = fields.Text(string='Patient Address')
    
    # Prescription Information
    prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription')
    prescriber_id = fields.Many2one('pharmacy.prescriber', string='Prescriber')
    prescriber_license = fields.Char(string='Prescriber License')
    
    # Transaction Details
    quantity = fields.Float(string='Quantity Dispensed', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', related='product_id.uom_id', readonly=True)
    
    # Sale Information
    pos_order_id = fields.Many2one('pos.order', string='POS Order')
    
    # Staff Information
    dispensed_by = fields.Many2one('res.users', string='Dispensed By', required=True, default=lambda self: self.env.user)
    pharmacist_id = fields.Many2one('res.users', string='Supervising Pharmacist', required=True)
    
    # Additional Information
    purpose = fields.Char(string='Purpose/Indication')
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                 default=lambda self: self.env.company)
    
    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.patient_name = self.patient_id.full_name
            self.patient_id_number = self.patient_id.id_number
            address_parts = [
                self.patient_id.street,
                self.patient_id.street2,
                self.patient_id.city,
                self.patient_id.county,
            ]
            self.patient_address = ', '.join(filter(None, address_parts))
    
    @api.onchange('prescription_id')
    def _onchange_prescription_id(self):
        if self.prescription_id:
            self.prescriber_id = self.prescription_id.prescriber_id
            self.prescriber_license = self.prescription_id.prescriber_id.license_number
