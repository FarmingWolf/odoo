/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { DashboardItem } from "./dashboard_item/dashboard_item";
// import { PieChart } from "./pie_chart/pie_chart";
import { items } from "./dashboard_items";
import { Dialog } from "@web/core/dialog/dialog";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { browser } from "@web/core/browser/browser";

class EstateDashboard extends Component {
    static template = "estate_dashboard.EstateDashboard";
    static components = { Layout, DashboardItem };

    setup() {
        this.action = useService("action");
        this.statistics = useState(useService("estate_dashboard.statistics"));
        this.dialog = useService("dialog");
        this.display = {
            controlPanel: {},
        };
        this.items = registry.category("estate_dashboard").getAll();
        this.state = useState({
            disabledItems: browser.localStorage.getItem("disabledDashboardItems")?.split(",") || []
        });
    }

    openConfiguration() {
        this.dialog.add(ConfigurationDialog, {
            items: this.items,
            disabledItems: this.state.disabledItems,
            onUpdateConfiguration: this.updateConfiguration.bind(this),
        })
    }

    updateConfiguration(newDisabledItems) {
        this.state.disabledItems = newDisabledItems;
    }

    openEstatePropertyDailyStatus() {
        this.action.doAction("estate_lease_contract.estate_lease_contract_property_daily_status_action");
    }

}

class ConfigurationDialog extends Component {
    static template = "estate_dashboard.ConfigurationDialog";
    static components = { Dialog, CheckBox };
    static props = ["close", "items", "disabledItems", "onUpdateConfiguration"];

    setup() {
        this.items = useState(this.props.items.map((item) => {
            return {
                ...item,
                enabled: !this.props.disabledItems.includes(item.id),
            }
        }));
    }

    done() {
        this.props.close();
    }

    onChange(checked, changedItem) {
        changedItem.enabled = checked;
        const newDisabledItems = Object.values(this.items).filter(
            (item) => !item.enabled
        ).map((item) => item.id)

        browser.localStorage.setItem(
            "disabledDashboardItems",
            newDisabledItems,
        );

        this.props.onUpdateConfiguration(newDisabledItems);
    }

}

registry.category("lazy_components").add("EstateDashboard", EstateDashboard);
