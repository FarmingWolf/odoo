/** @odoo-module */

import {registry} from "@web/core/registry";
import {reactive} from "@odoo/owl";

const statisticsService = {
    dependencies: ["rpc"],

    start(env, { rpc }) {

        const statistics = reactive({ isReady: false });

        async function loadData() {
            // 利用既存逻辑
            const updates = await rpc("/estate_dashboard/statistics");
            // const updates = await rpc("/estate_big_screen/statistics");
            Object.assign(statistics, updates, { isReady: true });
        }

        setInterval(loadData, 1000*60*30);
        loadData().then(r => {});

        return statistics;
    },
};

const lineChartDataService = {
    dependencies: ["rpc"],

    start(env, { rpc }) {

        const lineChartStatistics = reactive({ isReady: false,
            average_price_lst: [],
            rent_ratio_lst: [],
            rental_received_lst: [],
            rental_receivable_lst: [] });

        async function loadData() {
            try {
            const updates = await rpc("/estate_big_screen/statistics");
            Object.assign(lineChartStatistics, { ...updates, isReady: true,
                    average_price_lst: updates.average_price_lst || [],
                    rent_ratio_lst: updates.rent_ratio_lst || [],
                    rental_received_lst: updates.rental_received_lst || [],
                    rental_receivable_lst: updates.rental_receivable_lst || []
            });
        } catch (error) {
                console.error("Failed to load line chart data:", error);
            }
        }

        setInterval(loadData, 1000*60*30);
        loadData().then(r => {});

        // console.log(`lineChartStatistics:`, lineChartStatistics);
        return lineChartStatistics;
    },
};

const outOfRentProperties = {
    dependencies: ["rpc"],

    start(env, { rpc }) {

        const tgtProperties = reactive({
            data: [],
            isReady: false,
            isLoading: false,
            lastUpdated: null,
        });

        async function loadData() {
            try {
                tgtProperties.isLoading = true;
                // 利用既存逻辑
                const updates = await rpc("/estate_big_screen/get_out_of_rent_properties");
                // 判断是否是数组
                // 安全更新，不影响原来对象结构
                tgtProperties.data = Array.isArray(updates) ? updates : [];
                tgtProperties.isReady = true;
                tgtProperties.isLoading = false;
                tgtProperties.lastUpdated = new Date();
            } catch (error) {
                console.error("Failed to load out-of-rent properties", error);
                tgtProperties.data = [];
                tgtProperties.isReady = false;
                tgtProperties.isLoading = false;
            }
        }

        setInterval(loadData, 1000*60*30);
        loadData().then(r => {});
        console.log(`isReady in service `, tgtProperties.isReady);
        console.log(`tgtProperties in service `, tgtProperties);
        return tgtProperties;
    },

};

const companyName4BigScreenSvc = {
    dependencies: ["rpc"],

    start(env, { rpc }) {

        const companyNM = reactive({
            nm: "",
            isReady: false,
        });

        async function loadCompanyNM() {
            try {
                // 利用既存逻辑
                const company_nm = await rpc("/estate_big_screen/get_company_nm_4_big_screen");
                // 判断是否是数组
                // 安全更新，不影响原来对象结构
                debugger;
                companyNM.nm = company_nm ? Object.values(company_nm)[0] : "";
                companyNM.isReady = true;
            } catch (error) {
                console.error("Failed to load company_nm_4_big_screen", error);

            }
        }

        loadCompanyNM().then(r => {});
        return companyNM;
    },
};

registry.category("services").add("estate_big_screen.statistics", statisticsService);
registry.category("services").add("estate_big_screen.lineChartDataService", lineChartDataService);
registry.category("services").add("estate_big_screen.outOfRentProperties", outOfRentProperties);
registry.category("services").add("estate_big_screen.companyName4BigScreenSvc", companyName4BigScreenSvc);
