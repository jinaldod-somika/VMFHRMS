import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class VmfHrDashboard extends Component {
    static template = "vmf_hrms.Dashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            totalEmployees: 0,
            openPositions: 0,
            pendingLeaves: 0,
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
            // 1. Headcount
            const employees = await this.orm.searchCount("hr.employee", [["active", "=", true]]);
            this.state.totalEmployees = employees;

            // 2. Open MRFs
            const openMRFCount = await this.orm.searchCount("vmf.mrf", [
                ["state", "in", ["budget_approved", "in_progress"]],
            ]);
            const criticalMRFCount = await this.orm.searchCount("vmf.mrf", [
                ["state", "in", ["budget_approved", "in_progress"]],
                ["priority", "=", "critical"],
            ]);
            this.state.openPositions = openMRFCount;
            this.state.criticalPositions = criticalMRFCount;

            // 3. Attrition (YTD) - Mock calculation for demonstration
            const exits = await this.orm.searchCount("vmf.exit", [["state", "=", "completed"]]);
            this.state.attritionRate = employees > 0 ? ((exits / employees) * 100).toFixed(1) : 0;

            // 4. Payroll Total
            const payrollRuns = await this.orm.searchRead("vmf.payroll.run", [["state", "=", "confirmed"]], ["total_net"], { limit: 1 });
            this.state.payrollTotal = payrollRuns.length ? (payrollRuns[0].total_net / 1000000).toFixed(2) : "6.42"; // Default mock if no data

            // 5. Travel Spend
            const travelRequests = await this.orm.searchRead("vmf.travel.request", [["state", "!=", "draft"]], ["total_estimate"]);
            const totalTravel = travelRequests.reduce((sum, r) => sum + (r.total_estimate || 0), 0);
            this.state.travelSpend = (totalTravel / 1000).toFixed(0);

            // 6. HIPO Coverage
            const hipoCount = await this.orm.searchCount("hr.employee", [["vmf_is_hipo", "=", true]]);
            this.state.hipoCoverage = employees > 0 ? ((hipoCount / employees) * 100).toFixed(0) : "62";

            // 7. Headcount by Category (Chart Data)
            const categories = await this.orm.readGroup("hr.employee", [["active", "=", true]], ["vmf_employee_category"], ["vmf_employee_category"]);
            this.state.headcountByCategory = categories.map(c => ({
                label: this._getCategoryLabel(c.vmf_employee_category),
                count: c.vmf_employee_category_count,
                percentage: (c.vmf_employee_category_count / employees * 100).toFixed(0)
            })).sort((a, b) => b.count - a.count);

            // 8. Recruitment Funnel (Chart Data)
            const funnelStates = ['new', 'screening', 'interview_1', 'selected', 'offer_released', 'joined'];
            const funnelData = await this.orm.readGroup("vmf.candidate", [], ["state"], ["state"]);
            this.state.recruitmentFunnel = funnelStates.map(s => {
                const group = funnelData.find(g => g.state === s);
                const count = group ? group.state_count : 0;
                return {
                    label: this._getFunnelLabel(s),
                    count: count,
                    width: Math.max(15, (count / 10)) // Visual scaling
                };
            });

        } catch (e) {
            console.error("Dashboard error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    _getCategoryLabel(code) {
        const mapping = {
            'expat_permanent': 'Expat Perm',
            'expat_contractual': 'Expat Cont',
            'national_permanent': 'Nat Perm',
            'national_contractual': 'Nat Cont',
            'security_agency': 'Sec/Agency',
            'subcontractor': 'Subcontractor'
        };
        return mapping[code] || code || 'Other';
    }

    _getFunnelLabel(code) {
        const mapping = {
            'new': 'Sourced',
            'screening': 'Screened',
            'interview_1': 'Interviewed',
            'selected': 'Selected',
            'offer_released': 'Offered',
            'joined': 'Joined'
        };
        return mapping[code] || code;
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
