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
import { session } from "@web/session";

class EstateDashboard extends Component {
    static template = "estate_dashboard.EstateDashboard";
    static components = { Layout, DashboardItem };

    setup() {
        this.action = useService("action");
        this.statistics = useState(useService("estate_dashboard.statistics"));
        // 初始化统计数据
        // this.statisticsByCompany = useState(this.statistics.statisticsByCompany);
        this.dialog = useService("dialog");
        this.userService = useService("user");
        this.user = this.userService.user;
        this.display = {
            controlPanel: {},
        };
        this.items = registry.category("estate_dashboard").getAll();
        this.state = useState({
            disabledItems: browser.localStorage.getItem("disabledDashboardItems")?.split(",") || [],
            /** 202408250730 现在看以下四个不放在state中也无妨
            // statisticsByCompany: this.statistics.statisticsByCompany || {},
            // companies: session.allowed_companies || [],
            // defaultStatistics: { isReady: false, data: {} },
            // items: registry.category("estate_dashboard").getAll(),**/
            configurationSet: browser.localStorage.getItem("ConfigurationSet") || "no",
            allDataLoadedCnt: 0,
            allDataLoaded: false,
            displayed_ini:
                ['estate_conventional_quantity', 'estate_conventional_area_quantity',
                    'estate_conventional_lease_quantity', 'estate_conventional_area_lease_quantity',
                    'ratio_conventional_quantity', 'ratio_conventional_area_quantity',
                    'pie_chart_ratio_conventional_quantity', 'pie_chart_ratio_conventional_area_quantity'],
        });
        // 使用 userService 获取当前用户的信息
        const { user_companies } = session;
        this.companies = user_companies.allowed_companies;
        this.defaultStatistics = { isReady: false };
        console.log("Initialized companies:", this.companies);
        console.log("Initialized statistics:", this.statistics);
        console.log("Initialized statistics.isReady:", this.statistics.isReady);

        /**
        // 202408250730 从这里获取所有数据
        for (const companyId in user_companies.allowed_companies) {
            this.statistics.statisticsByCompany[companyId] = useState({isReady: false});
            this.statisticsByCompany[companyId] = useState({isReady: false});
            console.log(`从js loadData 开始 companyId ${companyId}`)
            this.statistics.loadData(companyId).then(r => {
                console.log(`从js loadData 完成 companyId ${companyId}:`, this.statistics.statisticsByCompany)
                console.log(`其中 ${companyId}statistics.statisticsByCompany:`, this.statistics.statisticsByCompany[companyId])
                Object.assign(this.statistics.statisticsByCompany[companyId], r, {isReady: true});
                Object.assign(this.statisticsByCompany[companyId], r, {isReady: true});
                console.log(`其中 ${companyId}的statisticsByCompany:`, this.statisticsByCompany[companyId])
                // let allLoadedCnt = 0
                // for (let eachCompany in Object.values(this.statistics.statisticsByCompany)){
                //     if (eachCompany.isReady){
                //         allLoadedCnt++;
                //     }
                // }
                this.state.allDataLoadedCnt++;

                if (this.state.allDataLoadedCnt === Object.values(this.statistics.statisticsByCompany).length){
                    this.state.allDataLoaded = true;
                    console.log(`最后 this.allDataLoaded = ${this.state.allDataLoaded}:`)
                }

                console.log(`this.allDataLoaded = ${this.state.allDataLoaded}；allLoadedCnt= ${this.state.allDataLoadedCnt}`)
            });
        }*/

    }

    /**
     * 这是从service中直接取得已经存在的statistics
     * @param companyId
     * @returns {{isReady}|*|{isReady: boolean}}
     */
    getCompanyStatistics(companyId) {
        console.log(`开始 getCompanyStatistics companyId:${companyId}`);
        console.log(`this.statisticsByCompany 长度→→→:${Object.values(this.statisticsByCompany).length}`);
        console.log(`this.statistics.statisticsByCompany 长度→→→:${Object.values(this.statistics.statisticsByCompany).length}`);
        console.log(`this.statistics.statisticsByCompany:${this.statistics.statisticsByCompany[companyId]}`);
        const stats = this.statisticsByCompany[companyId];
        console.log("getCompanyStatistics stats:", stats);

        if (stats && stats.isReady) {
            console.log(`stats ${companyId} ready! `);
            console.log(`stats ${companyId}`, stats);
            return stats;
        } else {
            // 如果数据尚未准备好，返回默认状态
            console.log(`stats  ${companyId} not Ready`);
            return this.defaultStatistics;
        }
    }

    /**
     * 通过service的loadData调用controller从DB取数据
     * @param companyId
     */
    async getCompanyStatisticsFromDB(companyId) {
        console.log("直接取companyId:", companyId);
        let statsPromise = await this.statistics.loadData(companyId);
        Object.assign(this.statisticsByCompany[companyId], statsPromise, {isReady: true});

        // 使用 .then() 方法等待 Promise 解析
        statsPromise.then(stats => {
            console.log("then中得到了companyId的stats:", stats);
            console.log("then中得到了companyId的stats。isReady:", stats.isReady);
            return statsPromise
        }).catch(error => {
            console.error('Error fetching statistics:', error);
        });
        console.log("得到了companyId的stats:", statsPromise);
        console.log("statistics===:", this.statistics);
        console.log("statisticsByCompany:", this.statisticsByCompany);
        console.log("得到了companyId的stats。isRead:", statsPromise.isReady);
        return statsPromise
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
        this.state.configurationSet = "yes";
    }


}

class ConfigurationDialog extends Component {
    static template = "estate_dashboard.ConfigurationDialog";
    static components = { Dialog, CheckBox };
    static props = ["close", "items", "disabledItems", "onUpdateConfiguration"];

    setup() {
        this.items = useState(this.props.items.map((item) => {
            const ini_display_items = ['estate_conventional_quantity', 'estate_conventional_area_quantity',
                'estate_conventional_lease_quantity', 'estate_conventional_area_lease_quantity',
                'ratio_conventional_quantity', 'ratio_conventional_area_quantity',
                'pie_chart_ratio_conventional_quantity', 'pie_chart_ratio_conventional_area_quantity']
            return {
                ...item,
                enabled: (browser.localStorage.getItem("ConfigurationSet") === "yes" && !this.props.disabledItems.includes(item.id)) ||
                    (browser.localStorage.getItem("ConfigurationSet") !== "yes" && ini_display_items.includes(item.id)),
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
            "ConfigurationSet",
            "yes",
        );
        browser.localStorage.setItem(
            "disabledDashboardItems",
            newDisabledItems,
        );

        this.props.onUpdateConfiguration(newDisabledItems);
    }

}

registry.category("lazy_components").add("EstateDashboard", EstateDashboard);
