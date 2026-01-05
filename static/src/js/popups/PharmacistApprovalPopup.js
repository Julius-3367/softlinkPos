/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

export class PharmacistApprovalPopup extends AbstractAwaitablePopup {
    static template = "softlink_pos.PharmacistApprovalPopup";
    static defaultProps = {
        confirmText: _t("Approve"),
        cancelText: _t("Cancel"),
        title: _t("Pharmacist Approval Required"),
    };

    setup() {
        super.setup();
        this.order = this.props.order;
        this.state = useState({
            pharmacistPin: "",
            notes: "",
        });
    }

    async confirm() {
        if (!this.state.pharmacistPin) {
            await this.env.services.popup.add('ErrorPopup', {
                title: _t("PIN Required"),
                body: _t("Please enter pharmacist PIN for approval."),
            });
            return;
        }

        // Verify pharmacist PIN
        const pharmacist = await this.rpc({
            model: "res.users",
            method: "search_read",
            domain: [
                ["pin", "=", this.state.pharmacistPin],
                ["groups_id", "in", [this.env.pos.config.module_pos_hr ? "softlink_pos.group_pharmacy_pharmacist" : false]],
            ],
            fields: ["id", "name"],
            limit: 1,
        });

        if (!pharmacist || pharmacist.length === 0) {
            await this.env.services.popup.add('ErrorPopup', {
                title: _t("Invalid PIN"),
                body: _t("Invalid pharmacist PIN or user is not a pharmacist."),
            });
            return;
        }

        // Approve the order
        this.order.approved_by_pharmacist = true;
        this.order.pharmacist_id = pharmacist[0].id;

        this.props.resolve({ confirmed: true, payload: pharmacist[0] });
    }
}
