# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class ExpiryAlertWizard(models.TransientModel):
    _name = 'pharmacy.expiry.alert.wizard'
    _description = 'Expiry Alert Wizard'

    days_threshold = fields.Integer(string='Days Threshold', default=90, required=True,
                                     help='Show products expiring within this many days')
    
    show_expired = fields.Boolean(string='Show Expired Products', default=True)
    show_near_expiry = fields.Boolean(string='Show Near Expiry Products', default=True)
    
    line_ids = fields.One2many('pharmacy.expiry.alert.line', 'wizard_id', string='Products')
    
    def action_generate_report(self):
        """Generate expiry alert report"""
        self.ensure_one()
        
        # Clear existing lines
        self.line_ids.unlink()
        
        today = fields.Date.today()
        threshold_date = today + timedelta(days=self.days_threshold)
        
        # Find all lots with expiry dates
        domain = [('expiry_date', '!=', False)]
        
        if not self.show_expired and not self.show_near_expiry:
            return {'type': 'ir.actions.act_window_close'}
        
        if not self.show_expired:
            domain.append(('expiry_date', '>=', today))
        
        if not self.show_near_expiry:
            domain.append(('expiry_date', '<', today))
        else:
            domain.append(('expiry_date', '<=', threshold_date))
        
        lots = self.env['stock.lot'].search(domain, order='expiry_date asc')
        
        lines_data = []
        for lot in lots:
            # Get available quantity
            quants = self.env['stock.quant'].search([
                ('lot_id', '=', lot.id),
                ('location_id.usage', '=', 'internal'),
            ])
            
            available_qty = sum(quants.mapped('quantity'))
            
            if available_qty > 0:
                lines_data.append({
                    'wizard_id': self.id,
                    'lot_id': lot.id,
                    'product_id': lot.product_id.id,
                    'expiry_date': lot.expiry_date,
                    'available_qty': available_qty,
                    'days_to_expiry': lot.days_to_expiry,
                    'is_expired': lot.is_expired,
                })
        
        self.env['pharmacy.expiry.alert.line'].create(lines_data)
        
        # Return action to show the wizard with results
        return {
            'name': 'Expiry Alert Report',
            'type': 'ir.actions.act_window',
            'res_model': 'pharmacy.expiry.alert.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
    
    def action_print_report(self):
        """Print expiry alert report"""
        return self.env.ref('softlink_pos.action_report_expiry_alert').report_action(self)


class ExpiryAlertLine(models.TransientModel):
    _name = 'pharmacy.expiry.alert.line'
    _description = 'Expiry Alert Line'
    _order = 'expiry_date asc'

    wizard_id = fields.Many2one('pharmacy.expiry.alert.wizard', string='Wizard', required=True, ondelete='cascade')
    
    lot_id = fields.Many2one('stock.lot', string='Lot/Batch', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True)
    available_qty = fields.Float(string='Available Quantity')
    days_to_expiry = fields.Integer(string='Days to Expiry')
    is_expired = fields.Boolean(string='Expired')
    
    status = fields.Char(string='Status', compute='_compute_status')
    
    @api.depends('is_expired', 'days_to_expiry')
    def _compute_status(self):
        for line in self:
            if line.is_expired:
                line.status = 'EXPIRED'
            elif line.days_to_expiry <= 30:
                line.status = 'CRITICAL'
            elif line.days_to_expiry <= 60:
                line.status = 'WARNING'
            else:
                line.status = 'ALERT'
