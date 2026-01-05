/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

export class PatientSelectionPopup extends AbstractAwaitablePopup {
    static template = "softlink_pos.PatientSelectionPopup";
    static defaultProps = {
        confirmText: _t("Select"),
        cancelText: _t("Cancel"),
        title: _t("Select Patient"),
        body: "",
    };

    setup() {
        super.setup();
        this.state = useState({
            searchQuery: "",
            patients: [],
            selectedPatient: null,
            showNewPatientForm: false,
            newPatient: {
                first_name: "",
                last_name: "",
                phone: "",
                date_of_birth: "",
                gender: "male",
                id_number: "",
            },
        });
        this.searchPatients();
    }

    async searchPatients() {
        const patients = await this.rpc({
            model: "pharmacy.patient",
            method: "search_read",
            domain: this.getSearchDomain(),
            fields: ["id", "full_name", "phone", "age", "gender", "id_number"],
            limit: 20,
        });
        this.state.patients = patients;
    }

    getSearchDomain() {
        const query = this.state.searchQuery.trim();
        if (!query) {
            return [];
        }
        return [
            "|",
            "|",
            ["full_name", "ilike", query],
            ["phone", "ilike", query],
            ["id_number", "ilike", query],
        ];
    }

    onSearchInput(event) {
        this.state.searchQuery = event.target.value;
        this.searchPatients();
    }

    selectPatient(patient) {
        this.state.selectedPatient = patient;
    }

    showNewForm() {
        this.state.showNewPatientForm = true;
    }

    hideNewForm() {
        this.state.showNewPatientForm = false;
    }

    async createPatient() {
        if (!this.state.newPatient.first_name || !this.state.newPatient.last_name || 
            !this.state.newPatient.phone || !this.state.newPatient.date_of_birth) {
            await this.env.services.popup.add('ErrorPopup', {
                title: _t("Missing Information"),
                body: _t("Please fill in all required fields (First Name, Last Name, Phone, Date of Birth)."),
            });
            return;
        }

        const patientId = await this.rpc({
            model: "pharmacy.patient",
            method: "create",
            args: [this.state.newPatient],
        });

        const patient = await this.rpc({
            model: "pharmacy.patient",
            method: "read",
            args: [[patientId], ["id", "full_name", "phone", "age", "gender"]],
        });

        this.state.selectedPatient = patient[0];
        this.state.showNewPatientForm = false;
    }

    async confirm() {
        if (this.state.selectedPatient) {
            this.props.resolve({ confirmed: true, payload: this.state.selectedPatient });
        } else {
            await this.env.services.popup.add('ErrorPopup', {
                title: _t("No Patient Selected"),
                body: _t("Please select a patient or create a new one."),
            });
        }
    }
}
