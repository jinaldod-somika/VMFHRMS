/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class VmfHrDashboard extends Component {
    static template = "vmf_hrms.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            totalEmployees: 0,
            openPositions: 0,
            travelRequests: 0,
            openGrievances: 0,
            loading: true,
        });
        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async loadStats() {
        this.state.loading = true;
        try {
            // Total active employees
            const employees = await this.orm.searchCount("hr.employee", [["active", "=", true]]);
            this.state.totalEmployees = employees;

            // Open positions (MRF)
            const openMRF = await this.orm.searchCount("vmf.mrf", [
                ["state", "in", ["budget_approved", "in_progress"]],
            ]);
            this.state.openPositions = openMRF;

            // Pending travel requests
            const travelPending = await this.orm.searchCount("vmf.travel.request", [
                ["state", "in", ["submitted", "manager_approved", "hr_approved", "travel_desk"]],
            ]);
            this.state.travelRequests = travelPending;

            // Open grievances
            const grievances = await this.orm.searchCount("vmf.grievance", [
                ["state", "not in", ["closed", "withdrawn"]],
            ]);
            this.state.openGrievances = grievances;

        } catch (e) {
            console.error("Dashboard load error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    openMRF() {
        this.action.doAction("vmf_hrms.action_vmf_mrf");
    }

    openTravel() {
        this.action.doAction("vmf_hrms.action_vmf_travel_request");
    }

    openGrievances() {
        this.action.doAction("vmf_hrms.action_vmf_grievance");
    }
}

registry.category("actions").add("vmf_hr_dashboard", VmfHrDashboard);
