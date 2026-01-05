# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    # Pharmacist on Duty
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist on Duty',
                                     domain=lambda self: [('groups_id', 'in', self.env.ref('softlink_pos.group_pharmacy_pharmacist').id)])
    
    # Controlled Drugs Count
    controlled_drugs_count = fields.Integer(string='Controlled Drugs Dispensed', 
                                             compute='_compute_controlled_drugs_count')
    
    # Prescription Count
    prescription_count = fields.Integer(string='Prescriptions Dispensed',
                                        compute='_compute_prescription_count')
    
    def _compute_controlled_drugs_count(self):
        for session in self:
            orders = self.env['pos.order'].search([('session_id', '=', session.id)])
            count = 0
            for order in orders:
                if order.has_controlled_drugs:
                    count += 1
            session.controlled_drugs_count = count
    
    def _compute_prescription_count(self):
        for session in self:
            session.prescription_count = self.env['pos.order'].search_count([
                ('session_id', '=', session.id),
                ('prescription_id', '!=', False)
            ])
    
    def action_pos_session_open(self):
        """Override to check if pharmacist is assigned"""
        for session in self:
            if session.config_id.is_pharmacy_pos and session.config_id.require_pharmacist_approval:
                if not session.pharmacist_id:
                    raise UserError('Please assign a pharmacist on duty before opening the session.')
        return super(PosSession, self).action_pos_session_open()
