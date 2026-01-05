# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import requests
import json
import base64
from datetime import datetime

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
    
    payment_type = fields.Selection([
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('insurance', 'Insurance'),
        ('bank', 'Bank Transfer'),
    ], string='Payment Type', default='cash')
    
    # M-Pesa Configuration
    mpesa_shortcode = fields.Char(string='M-Pesa Shortcode')
    mpesa_consumer_key = fields.Char(string='Consumer Key')
    mpesa_consumer_secret = fields.Char(string='Consumer Secret')
    mpesa_passkey = fields.Char(string='Pass Key')
    mpesa_environment = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('production', 'Production'),
    ], string='Environment', default='sandbox')
    
    # Insurance Configuration
    insurance_company_id = fields.Many2one('res.partner', string='Insurance Company')
    insurance_api_url = fields.Char(string='API URL')
    insurance_api_key = fields.Char(string='API Key')


class PosPayment(models.Model):
    _inherit = 'pos.payment'
    
    payment_type = fields.Selection(related='payment_method_id.payment_type', store=True)
    
    # M-Pesa Fields
    mpesa_transaction_id = fields.Char(string='M-Pesa Transaction ID')
    mpesa_phone = fields.Char(string='M-Pesa Phone Number')
    mpesa_receipt_number = fields.Char(string='M-Pesa Receipt')
    mpesa_status = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='M-Pesa Status', default='pending')
    
    # Insurance Fields
    insurance_member_number = fields.Char(string='Insurance Member Number')
    insurance_authorization_code = fields.Char(string='Authorization Code')
    insurance_claim_number = fields.Char(string='Claim Number')
    insurance_copay_amount = fields.Float(string='Co-pay Amount')
    insurance_covered_amount = fields.Float(string='Insurance Covered')
    
    # Change calculation
    amount_tendered = fields.Float(string='Amount Tendered')
    change_amount = fields.Float(string='Change', compute='_compute_change_amount', store=True)
    
    @api.depends('amount_tendered', 'amount')
    def _compute_change_amount(self):
        for payment in self:
            if payment.payment_type == 'cash' and payment.amount_tendered:
                payment.change_amount = payment.amount_tendered - payment.amount
            else:
                payment.change_amount = 0.0
    
    def initiate_mpesa_stk_push(self):
        """Initiate M-Pesa STK Push"""
        self.ensure_one()
        
        if not self.mpesa_phone:
            raise UserError('Please provide M-Pesa phone number')
        
        payment_method = self.payment_method_id
        
        # Get access token
        access_token = self._get_mpesa_access_token()
        
        # Prepare STK Push request
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        shortcode = payment_method.mpesa_shortcode
        passkey = payment_method.mpesa_passkey
        
        password_str = f"{shortcode}{passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode('utf-8')
        
        # Format phone number (remove +254, add 254)
        phone = self.mpesa_phone.replace('+', '').replace(' ', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('254'):
            pass
        else:
            phone = '254' + phone
        
        # API URL
        if payment_method.mpesa_environment == 'sandbox':
            url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        else:
            url = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'BusinessShortCode': shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(self.amount),
            'PartyA': phone,
            'PartyB': shortcode,
            'PhoneNumber': phone,
            'CallBackURL': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/mpesa/callback',
            'AccountReference': self.pos_order_id.name or 'ORDER',
            'TransactionDesc': f'Payment for {self.pos_order_id.name}',
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response_data = response.json()
            
            if response_data.get('ResponseCode') == '0':
                self.write({
                    'mpesa_transaction_id': response_data.get('CheckoutRequestID'),
                    'mpesa_status': 'pending',
                })
                return {
                    'success': True,
                    'message': 'STK Push sent successfully. Please check your phone.',
                    'checkout_request_id': response_data.get('CheckoutRequestID'),
                }
            else:
                raise UserError(f"M-Pesa Error: {response_data.get('errorMessage', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            raise UserError(f'Failed to connect to M-Pesa: {str(e)}')
    
    def _get_mpesa_access_token(self):
        """Get M-Pesa OAuth access token"""
        payment_method = self.payment_method_id
        
        if payment_method.mpesa_environment == 'sandbox':
            url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        else:
            url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        
        consumer_key = payment_method.mpesa_consumer_key
        consumer_secret = payment_method.mpesa_consumer_secret
        
        if not consumer_key or not consumer_secret:
            raise UserError('M-Pesa credentials not configured')
        
        auth_string = f"{consumer_key}:{consumer_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {auth_bytes}',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response_data = response.json()
            
            if 'access_token' in response_data:
                return response_data['access_token']
            else:
                raise UserError('Failed to get M-Pesa access token')
                
        except requests.exceptions.RequestException as e:
            raise UserError(f'Failed to authenticate with M-Pesa: {str(e)}')
    
    def verify_insurance_coverage(self):
        """Verify insurance coverage for patient"""
        self.ensure_one()
        
        if not self.insurance_member_number:
            raise UserError('Please provide insurance member number')
        
        patient = self.pos_order_id.patient_id
        if not patient:
            raise UserError('Patient information required for insurance claims')
        
        # This is a placeholder for actual insurance API integration
        # Each insurance company has different API
        
        return {
            'success': True,
            'member_name': patient.full_name,
            'member_number': self.insurance_member_number,
            'coverage_limit': 50000.00,
            'used_amount': 10000.00,
            'available_amount': 40000.00,
            'copay_percentage': 10.0,
        }
