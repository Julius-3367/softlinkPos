/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.patient_id = this.patient_id || null;
        this.patient_name = this.patient_name || '';
        this.patient_phone = this.patient_phone || '';
        this.prescription_id = this.prescription_id || null;
        this.insurance_claim = this.insurance_claim || false;
        this.insurance_company = this.insurance_company || '';
        this.insurance_number = this.insurance_number || '';
        this.insurance_amount = this.insurance_amount || 0.0;
        this.patient_copay = this.patient_copay || 0.0;
        this.approved_by_pharmacist = this.approved_by_pharmacist || false;
        this.pharmacist_id = this.pharmacist_id || null;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.patient_id = this.patient_id;
        json.patient_name = this.patient_name;
        json.patient_phone = this.patient_phone;
        json.prescription_id = this.prescription_id;
        json.insurance_claim = this.insurance_claim;
        json.insurance_company = this.insurance_company;
        json.insurance_number = this.insurance_number;
        json.insurance_amount = this.insurance_amount;
        json.patient_copay = this.patient_copay;
        json.approved_by_pharmacist = this.approved_by_pharmacist;
        json.pharmacist_id = this.pharmacist_id;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.patient_id = json.patient_id;
        this.patient_name = json.patient_name;
        this.patient_phone = json.patient_phone;
        this.prescription_id = json.prescription_id;
        this.insurance_claim = json.insurance_claim;
        this.insurance_company = json.insurance_company;
        this.insurance_number = json.insurance_number;
        this.insurance_amount = json.insurance_amount;
        this.patient_copay = json.patient_copay;
        this.approved_by_pharmacist = json.approved_by_pharmacist;
        this.pharmacist_id = json.pharmacist_id;
    },

    setPatient(patient) {
        this.patient_id = patient ? patient.id : null;
        this.patient_name = patient ? patient.full_name : '';
        this.patient_phone = patient ? patient.phone : '';
        if (patient && patient.has_insurance) {
            this.insurance_claim = true;
            this.insurance_company = patient.insurance_company || '';
            this.insurance_number = patient.insurance_number || '';
        }
    },

    setPrescription(prescription) {
        this.prescription_id = prescription ? prescription.id : null;
        if (prescription && prescription.patient_id) {
            // Auto-set patient from prescription
            this.setPatient(prescription.patient_id[0]);
        }
    },

    requiresPharmacistApproval() {
        return this.get_orderlines().some(line => {
            const product = line.get_product();
            return product.requires_prescription || 
                   (product.product_tmpl_id && product.product_tmpl_id.requires_prescription);
        });
    },

    hasPrescriptionItems() {
        return this.get_orderlines().some(line => {
            const product = line.get_product();
            return product.requires_prescription || 
                   (product.product_tmpl_id && product.product_tmpl_id.requires_prescription);
        });
    },

    hasControlledDrugs() {
        return this.get_orderlines().some(line => {
            const product = line.get_product();
            return product.drug_category === 'controlled';
        });
    },
});
