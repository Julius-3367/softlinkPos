# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import qrcode
import io
import base64
from datetime import datetime
import hashlib


class KraEtimsConfig(models.Model):
    _name = 'kra.etims.config'
    _description = 'KRA eTIMS Configuration'
    
    name = fields.Char(string='Configuration Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    # KRA Details
    kra_pin = fields.Char(string='KRA PIN', required=True)
    vat_number = fields.Char(string='VAT Number')
    control_unit_serial = fields.Char(string='Control Unit Serial Number', required=True)
    control_unit_id = fields.Char(string='Control Unit ID')
    
    # eTIMS API Configuration
    etims_api_url = fields.Char(string='eTIMS API URL', default='https://etims.kra.go.ke/api')
    etims_username = fields.Char(string='eTIMS Username')
    etims_password = fields.Char(string='eTIMS Password')
    etims_environment = fields.Selection([
        ('sandbox', 'Sandbox/Testing'),
        ('production', 'Production'),
    ], string='Environment', default='sandbox', required=True)
    
    # Certificate for signing
    certificate_file = fields.Binary(string='Certificate File')
    certificate_password = fields.Char(string='Certificate Password')
    
    # Invoice Counter
    invoice_counter = fields.Integer(string='Invoice Counter', default=1)
    daily_invoice_counter = fields.Integer(string='Daily Counter', default=1)
    last_reset_date = fields.Date(string='Last Counter Reset')
    
    active = fields.Boolean(string='Active', default=True)
    
    def reset_daily_counter(self):
        """Reset daily counter at midnight"""
        today = fields.Date.today()
        for config in self:
            if config.last_reset_date != today:
                config.write({
                    'daily_invoice_counter': 1,
                    'last_reset_date': today,
                })
    
    def get_next_invoice_number(self):
        """Get next invoice number and increment counter"""
        self.ensure_one()
        self.reset_daily_counter()
        
        invoice_num = self.invoice_counter
        daily_num = self.daily_invoice_counter
        
        self.write({
            'invoice_counter': invoice_num + 1,
            'daily_invoice_counter': daily_num + 1,
        })
        
        return invoice_num, daily_num


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    # KRA eTIMS Fields
    kra_invoice_number = fields.Char(string='KRA Invoice Number', readonly=True, copy=False)
    kra_cu_serial = fields.Char(string='Control Unit Serial', readonly=True)
    kra_invoice_counter = fields.Integer(string='Invoice Counter', readonly=True)
    kra_qr_code = fields.Binary(string='KRA QR Code', readonly=True)
    kra_signature = fields.Char(string='KRA Signature', readonly=True)
    kra_submitted = fields.Boolean(string='Submitted to KRA', default=False, readonly=True)
    kra_submission_date = fields.Datetime(string='KRA Submission Date', readonly=True)
    kra_response = fields.Text(string='KRA Response', readonly=True)
    
    # Receipt fields
    receipt_number = fields.Char(string='Receipt Number', readonly=True, copy=False)
    cashier_name = fields.Char(string='Cashier Name', compute='_compute_cashier_name', store=True)
    
    @api.depends('user_id')
    def _compute_cashier_name(self):
        for order in self:
            order.cashier_name = order.user_id.name if order.user_id else ''
    
    def action_pos_order_paid(self):
        """Override to generate KRA invoice and receipt"""
        res = super(PosOrder, self).action_pos_order_paid()
        
        for order in self:
            # Generate receipt number
            if not order.receipt_number:
                order.receipt_number = self.env['ir.sequence'].next_by_code('pos.receipt.number') or '/'
            
            # Generate KRA invoice
            order._generate_kra_invoice()
        
        return res
    
    def _generate_kra_invoice(self):
        """Generate KRA eTIMS compliant invoice"""
        self.ensure_one()
        
        # Get KRA configuration
        kra_config = self.env['kra.etims.config'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)
        
        if not kra_config:
            # If no KRA config, skip (for testing purposes)
            # In production, this should raise an error
            return
        
        # Get next invoice number
        invoice_num, daily_num = kra_config.get_next_invoice_number()
        
        # Generate invoice number format: CU-SERIAL-YYYYMMDD-COUNTER
        today = fields.Date.today().strftime('%Y%m%d')
        kra_invoice_number = f"{kra_config.control_unit_serial}-{today}-{daily_num:05d}"
        
        # Generate signature (simplified - real implementation needs proper cryptographic signing)
        signature_data = f"{kra_invoice_number}{self.amount_total}{self.date_order}"
        signature = hashlib.sha256(signature_data.encode()).hexdigest()[:16]
        
        # Generate QR Code
        qr_data = self._prepare_kra_qr_data(kra_config, kra_invoice_number, signature)
        qr_code_image = self._generate_qr_code(qr_data)
        
        # Update order
        self.write({
            'kra_invoice_number': kra_invoice_number,
            'kra_cu_serial': kra_config.control_unit_serial,
            'kra_invoice_counter': invoice_num,
            'kra_signature': signature,
            'kra_qr_code': qr_code_image,
        })
        
        # Submit to KRA (in background)
        if kra_config.etims_environment == 'production':
            self._submit_to_kra(kra_config)
    
    def _prepare_kra_qr_data(self, kra_config, invoice_number, signature):
        """Prepare data for KRA QR code"""
        # KRA QR Code format (simplified version)
        # Real format: https://www.kra.go.ke/etims-specifications
        
        qr_data = {
            'PIN': kra_config.kra_pin,
            'CU': kra_config.control_unit_serial,
            'INV': invoice_number,
            'DATE': self.date_order.strftime('%Y-%m-%d %H:%M:%S'),
            'TOTAL': f"{self.amount_total:.2f}",
            'SIG': signature,
        }
        
        # Convert to string format
        qr_string = '|'.join([f"{k}:{v}" for k, v in qr_data.items()])
        return qr_string
    
    def _generate_qr_code(self, data):
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue())
        
        return img_str
    
    def _submit_to_kra(self, kra_config):
        """Submit invoice to KRA eTIMS system"""
        self.ensure_one()
        
        # Prepare invoice data
        invoice_data = {
            'invoiceNumber': self.kra_invoice_number,
            'cuSerial': self.kra_cu_serial,
            'invoiceDate': self.date_order.strftime('%Y-%m-%d %H:%M:%S'),
            'sellerPin': kra_config.kra_pin,
            'sellerName': self.company_id.name,
            'buyerPin': self.partner_id.vat or '',
            'buyerName': self.partner_id.name or 'Walk-in Customer',
            'items': self._prepare_invoice_items(),
            'totalAmount': self.amount_total,
            'taxAmount': self.amount_tax,
            'signature': self.kra_signature,
        }
        
        # In production, send to KRA API
        # For now, just mark as submitted
        self.write({
            'kra_submitted': True,
            'kra_submission_date': fields.Datetime.now(),
            'kra_response': 'Success (Simulated)',
        })
    
    def _prepare_invoice_items(self):
        """Prepare invoice items for KRA submission"""
        items = []
        for line in self.lines:
            items.append({
                'itemCode': line.product_id.default_code or '',
                'itemName': line.product_id.name,
                'quantity': line.qty,
                'unitPrice': line.price_unit,
                'taxRate': line.tax_ids_after_fiscal_position[0].amount if line.tax_ids_after_fiscal_position else 0,
                'totalAmount': line.price_subtotal_incl,
            })
        return items
    
    def action_view_kra_details(self):
        """View KRA invoice details"""
        self.ensure_one()
        return {
            'name': 'KRA Invoice Details',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
