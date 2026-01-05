/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    async _onClickPay() {
        const order = this.pos.get_order();
        
        // Check for prescription items
        if (order.hasPrescriptionItems()) {
            if (!order.prescription_id && !order.patient_id) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Prescription Required'),
                    body: this.env._t('This order contains prescription items. Please add patient information and prescription before proceeding.'),
                });
                return;
            }
        }

        // Check for pharmacist approval
        if (order.requiresPharmacistApproval() && !order.approved_by_pharmacist) {
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Pharmacist Approval Required'),
                body: this.env._t('This order contains items that require pharmacist approval. Do you want to request approval?'),
            });
            
            if (confirmed) {
                // Show pharmacist approval popup
                await this.showPopup('PharmacistApprovalPopup', {
                    order: order,
                });
                
                if (!order.approved_by_pharmacist) {
                    return;
                }
            } else {
                return;
            }
        }

        // Check for expired products
        const expiredLines = order.get_orderlines().filter(line => {
            return line.lot_id && line.lot_id.is_expired;
        });

        if (expiredLines.length > 0 && this.pos.config.block_expired_products) {
            await this.showPopup('ErrorPopup', {
                title: this.env._t('Expired Products'),
                body: this.env._t('This order contains expired products. Please remove them before proceeding.'),
            });
            return;
        }

        // Continue with standard payment flow
        return super._onClickPay(...arguments);
    },
});
