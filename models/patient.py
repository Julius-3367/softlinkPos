# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Patient(models.Model):
    _name = 'pharmacy.patient'
    _description = 'Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'

    # Personal Information
    first_name = fields.Char(string='First Name', required=True, tracking=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True, tracking=True)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', store=True)
    
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', required=True)
    
    # Contact Information
    phone = fields.Char(string='Phone Number', required=True, tracking=True)
    email = fields.Char(string='Email')
    id_number = fields.Char(string='ID/Passport Number', tracking=True)
    
    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    county = fields.Char(string='County')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.ref('base.ke'))
    
    # Medical Information
    blood_group = fields.Selection([
        ('a+', 'A+'),
        ('a-', 'A-'),
        ('b+', 'B+'),
        ('b-', 'B-'),
        ('ab+', 'AB+'),
        ('ab-', 'AB-'),
        ('o+', 'O+'),
        ('o-', 'O-'),
    ], string='Blood Group')
    
    allergies = fields.Text(string='Known Allergies')
    chronic_conditions = fields.Text(string='Chronic Conditions')
    current_medications = fields.Text(string='Current Medications')
    
    # Insurance Information
    has_insurance = fields.Boolean(string='Has Insurance', default=False)
    insurance_company = fields.Char(string='Insurance Company')
    insurance_number = fields.Char(string='Insurance Number')
    insurance_expiry = fields.Date(string='Insurance Expiry Date')
    
    # Prescription History
    prescription_ids = fields.One2many('pharmacy.prescription', 'patient_id', string='Prescriptions')
    prescription_count = fields.Integer(string='Total Prescriptions', compute='_compute_prescription_count')
    
    # POS Orders
    pos_order_ids = fields.One2many('pos.order', 'patient_id', string='POS Orders')
    pos_order_count = fields.Integer(string='Total Orders', compute='_compute_pos_order_count')
    
    # Emergency Contact
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Relationship')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Additional Notes')
    
    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            names = [record.first_name or '', record.middle_name or '', record.last_name or '']
            record.full_name = ' '.join(filter(None, names))
    
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for record in self:
            if record.date_of_birth:
                record.age = today.year - record.date_of_birth.year - \
                            ((today.month, today.day) < (record.date_of_birth.month, record.date_of_birth.day))
            else:
                record.age = 0
    
    @api.depends('prescription_ids')
    def _compute_prescription_count(self):
        for record in self:
            record.prescription_count = len(record.prescription_ids)
    
    @api.depends('pos_order_ids')
    def _compute_pos_order_count(self):
        for record in self:
            record.pos_order_count = len(record.pos_order_ids)
    
    @api.constrains('phone')
    def _check_phone(self):
        for record in self:
            if record.phone:
                # Basic validation for Kenyan phone numbers
                phone = record.phone.replace('+', '').replace(' ', '').replace('-', '')
                if not phone.isdigit() or len(phone) < 10:
                    raise ValidationError('Please enter a valid phone number')
    
    @api.constrains('id_number')
    def _check_unique_id(self):
        for record in self:
            if record.id_number:
                existing = self.search([
                    ('id_number', '=', record.id_number),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(f'A patient with ID/Passport number {record.id_number} already exists')
    
    def action_view_prescriptions(self):
        return {
            'name': 'Patient Prescriptions',
            'type': 'ir.actions.act_window',
            'res_model': 'pharmacy.prescription',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id}
        }
    
    def action_view_orders(self):
        return {
            'name': 'Patient Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id}
        }
