/** @odoo-module **/
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

const chartLoaderService = {
    dependencies: [],
    async start() {
        await loadBundle("web.chartjs_lib");
        return true; // 返回加载状态
    }
};
registry.category("services").add("chart_loader", chartLoaderService);
