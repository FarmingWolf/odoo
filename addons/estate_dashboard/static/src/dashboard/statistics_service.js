/** @odoo-module */

import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { reactive } from "@odoo/owl";

const statisticsService = {
    dependencies: ["rpc"],
    start(env, { rpc }) {

        const statistics = reactive({ isReady: false });

        async function loadData() {
            const updates = await rpc("/estate_dashboard/statistics");
            Object.assign(statistics, updates, { isReady: true });
        }

        setInterval(loadData, 1000*60*60);
        loadData();

        return statistics;
    },
};

registry.category("services").add("estate_dashboard.statistics", statisticsService);
