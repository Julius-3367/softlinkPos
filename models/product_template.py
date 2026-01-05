# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_pharmaceutical = fields.Boolean(string='Is Pharmaceutical Product', default=False)
    pharmacy_product_id = fields.Many2one('pharmacy.product', string='Pharmacy Details', ondelete='cascade')
    
    # Quick access fields
    requires_prescription = fields.Boolean(string='Requires Prescription', related='pharmacy_product_id.requires_prescription', readonly=True)
    drug_category = fields.Selection(related='pharmacy_product_id.drug_category', readonly=True, store=True)
    dosage_form = fields.Selection(related='pharmacy_product_id.dosage_form', readonly=True)
    
    available_in_pos = fields.Boolean(string='Available in POS', default=True)
    
    @api.model
    def create(self, vals):
        product = super(ProductTemplate, self).create(vals)
        if vals.get('is_pharmaceutical'):
            self.env['pharmacy.product'].create({
                'name': product.name,
                'product_id': product.product_variant_id.id,
                'generic_name': vals.get('name', ''),
                'active_ingredient': vals.get('description_sale', '') or product.name,
                'dosage_form': vals.get('dosage_form', 'tablet'),
                'drug_category': vals.get('drug_category', 'otc'),
            })
        return product
