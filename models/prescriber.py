# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Prescriber(models.Model):
    _name = 'pharmacy.prescriber'
    _description = 'Medical Prescriber'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Full Name', required=True, tracking=True)
    title = fields.Selection([
        ('dr', 'Dr.'),
        ('prof', 'Prof.'),
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('ms', 'Ms.'),
    ], string='Title', default='dr')
    
    # Professional Details
    license_number = fields.Char(string='Medical License Number', required=True, tracking=True)
    license_authority = fields.Char(string='Licensing Authority', default='Kenya Medical Practitioners and Dentists Council')
    license_expiry = fields.Date(string='License Expiry Date')
    
    specialization = fields.Selection([
        ('general', 'General Practitioner'),
        ('pediatrics', 'Pediatrics'),
        ('surgery', 'Surgery'),
        ('internal', 'Internal Medicine'),
        ('obstetrics', 'Obstetrics & Gynecology'),
        ('psychiatry', 'Psychiatry'),
        ('cardiology', 'Cardiology'),
        ('dermatology', 'Dermatology'),
        ('orthopedics', 'Orthopedics'),
        ('ent', 'ENT'),
        ('ophthalmology', 'Ophthalmology'),
        ('dentistry', 'Dentistry'),
        ('other', 'Other'),
    ], string='Specialization', required=True, default='general')
    
    other_specialization = fields.Char(string='Other Specialization')
    
    # Contact Information
    phone = fields.Char(string='Phone Number', required=True)
    email = fields.Char(string='Email')
    
    # Facility Information
    facility_name = fields.Char(string='Facility/Hospital Name')
    facility_address = fields.Text(string='Facility Address')
    
    # Prescription History
    prescription_ids = fields.One2many('pharmacy.prescription', 'prescriber_id', string='Prescriptions')
    prescription_count = fields.Integer(string='Total Prescriptions', compute='_compute_prescription_count')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    is_verified = fields.Boolean(string='Verified', default=False, tracking=True,
                                  help='Indicates if the prescriber credentials have been verified')
    verification_date = fields.Date(string='Verification Date')
    verified_by = fields.Many2one('res.users', string='Verified By')
    
    notes = fields.Text(string='Notes')
    
    @api.depends('prescription_ids')
    def _compute_prescription_count(self):
        for record in self:
            record.prescription_count = len(record.prescription_ids)
    
    @api.constrains('license_number')
    def _check_unique_license(self):
        for record in self:
            if record.license_number:
                existing = self.search([
                    ('license_number', '=', record.license_number),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(f'A prescriber with license number {record.license_number} already exists')
    
    @api.constrains('license_expiry')
    def _check_license_expiry(self):
        for record in self:
            if record.license_expiry and record.license_expiry < fields.Date.today():
                raise ValidationError(f'License for {record.name} has expired. Cannot accept prescriptions from expired licenses.')
    
    def action_verify_prescriber(self):
        self.write({
            'is_verified': True,
            'verification_date': fields.Date.today(),
            'verified_by': self.env.user.id,
        })
    
    def action_view_prescriptions(self):
        return {
            'name': 'Prescriber Prescriptions',
            'type': 'ir.actions.act_window',
            'res_model': 'pharmacy.prescription',
            'view_mode': 'tree,form',
            'domain': [('prescriber_id', '=', self.id)],
            'context': {'default_prescriber_id': self.id}
        }
    
    @api.model
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.title or ''} {record.name}".strip()
            if record.license_number:
                name = f"{name} ({record.license_number})"
            result.append((record.id, name))
        return result
