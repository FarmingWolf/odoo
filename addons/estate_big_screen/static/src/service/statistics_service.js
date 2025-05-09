/** @odoo-module */

import {registry} from "@web/core/registry";
import {reactive} from "@odoo/owl";

export class StatisticsService {

    constructor(env, { rpc }) {
        this.rpc = rpc;
        this.statistics = reactive({
            isReady: false,
            ...JSON.parse(localStorage.getItem('estate_stats') || '{}')
        });
        this.initialized = false;
        this.intervalId = null;
    }
    async loadData() {
        try {
            // 利用既存逻辑
            const updates = await this.rpc("/estate_dashboard/statistics");
            Object.assign(this.statistics, updates, {isReady: true});
            // 缓存数据到本地存储
            localStorage.setItem('estate_stats', JSON.stringify({
                ...updates,
                isReady: true
            }));
        } catch (error) {
            console.error("Failed to load statistics:", error);
            this.statistics.isReady = false;
        }
    }

    initialize() {
        if (!this.initialized) {
            this.initialized = true;
            this.loadData();
            this.intervalId = setInterval(() => this.loadData(), 1000 * 60 * 30);
        }
    }

    destroy() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
}

export const statisticsService = {
    dependencies: ["rpc"],
    start(env, services) {
        const service = new StatisticsService(env, services);

        return new Proxy(service, {
            get(target, prop) {
                if (prop === 'destroy') return target[prop];
                // 当访问任何属性时自动初始化
                debugger;
                if (!target.initialized) {
                    target.initialize();
                }
                // 返回整个 statistics 对象或特定属性
                if (prop === 'statistics') {
                    return target.statistics;
                }
                // 优先从 statistics 对象获取属性
                if (prop in target.statistics) {
                    return target.statistics[prop];
                }
                return target.statistics[prop];
            }
        });
    },
};

export const lineChartDataService = {
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

export const outOfRentProperties = {
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

export const companyName4BigScreenSvc = {
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
