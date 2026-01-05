# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class StockLot(models.Model):
    _inherit = 'stock.lot'

    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    manufacturing_date = fields.Date(string='Manufacturing Date')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_expiry_status', store=True)
    is_near_expiry = fields.Boolean(string='Near Expiry', compute='_compute_expiry_status', store=True)
    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_expiry_status', store=True)
    
    batch_number = fields.Char(string='Batch Number', copy=False)
    supplier_batch_no = fields.Char(string='Supplier Batch Number')
    
    # Pharmacy specific
    pharmacy_product_id = fields.Many2one('pharmacy.product', string='Pharmacy Product', 
                                          compute='_compute_pharmacy_product', store=True)
    
    @api.depends('product_id')
    def _compute_pharmacy_product(self):
        for record in self:
            pharmacy = self.env['pharmacy.product'].search([('product_id', '=', record.product_id.id)], limit=1)
            record.pharmacy_product_id = pharmacy.id if pharmacy else False
    
    @api.depends('expiry_date')
    def _compute_expiry_status(self):
        today = fields.Date.today()
        for record in self:
            if record.expiry_date:
                record.days_to_expiry = (record.expiry_date - today).days
                record.is_expired = record.expiry_date < today
                
                # Get alert days from pharmacy product
                alert_days = 90
                if record.pharmacy_product_id:
                    alert_days = record.pharmacy_product_id.expiry_alert_days or 90
                
                record.is_near_expiry = 0 < record.days_to_expiry <= alert_days
            else:
                record.days_to_expiry = 0
                record.is_expired = False
                record.is_near_expiry = False
    
    @api.constrains('expiry_date')
    def _check_expiry_date(self):
        for record in self:
            if record.expiry_date and record.is_expired:
                # Just warning, don't block - might be receiving expired stock to destroy
                pass
