/** @odoo-module */

import { registry } from "@web/core/registry";
import { LazyComponent } from "@web/core/assets";
import { Component, xml } from "@odoo/owl";

class EstateDashboardLoader extends Component {
    static components = { LazyComponent };
    static template = xml`
    <LazyComponent bundle="'estate_dashboard.dashboard'" Component="'EstateDashboard'" props="props"/>
    `;

}

registry.category("actions").add("estate_dashboard.dashboard", EstateDashboardLoader);
