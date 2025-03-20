/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { getCurrency } from '@web/core/currency';
import { Component, onWillStart, useState } from "@odoo/owl";

export class FundManagementDashboard extends Component {

    setup() {
        super.setup();
        this.orm = useService('orm');

        this.state = useState({
            expenses: {}
        });

        onWillStart(async () => {
            const expense_states = await this.orm.call("fund.management", 'get_fund_management_dashboard', []);
            this.state.expenses = expense_states;
        });
    }

    renderMonetaryField(value, currency_id) {
        value = value.toFixed(2);
        const currency = getCurrency(currency_id);
        if (currency) {
            if (currency.position === "after") {
                value += currency.symbol;
            } else {
                value = currency.symbol + value;
            }
        }
        return value;
    }
}
FundManagementDashboard.template = 'fund_management.FundManagementDashboard';
