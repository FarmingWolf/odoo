/** @odoo-module **/

import {Component, onMounted, onWillUnmount, useEffect, useState, reactive, onWillStart} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {Layout} from "@web/search/layout";
import {ClockComponent} from "./js/clock_component"
import {PieChartCard} from "./component/pie_chart_card/pie_chart_card";
import {LineChart} from "./component/line_chart/line_chart";
import {DoughnutChart} from "./component/doughnut_chart/doughnut_chart";
import {ScrollingDataGrid} from "./component/scrolling_datagrid/scrolling_datagrid";
import {SharedInfoComponent} from "./component/scrolling_datagrid/shared_info";

class EstateBigScreen extends Component {
    static template = "estate_big_screen.EstateBigScreen";
    static components = { Layout, ClockComponent, PieChartCard, LineChart, DoughnutChart, ScrollingDataGrid, SharedInfoComponent };

    setup() {
        this.display = {
            controlPanel: false,
        };

        onMounted(() => {
            // 进入页面时隐藏导航栏
            document.querySelector('.o_main_navbar')?.classList.add('d-none');
            document.querySelector('.o_sub_menu')?.classList.add('d-none');
        });

        onWillUnmount(() => {
            // 离开页面时恢复导航栏
            document.querySelector('.o_main_navbar')?.classList.remove('d-none');
            document.querySelector('.o_sub_menu')?.classList.remove('d-none');
        });

        this.statistics = useState(useService("estate_big_screen.statistics"));
        this.lineChartStatistics = useState(useService("estate_big_screen.lineChartDataService"));
        if (!this.lineChartStatistics["average_price_lst"]) {
            this.lineChartStatistics["average_price_lst"] = [];
        }
        if (!this.lineChartStatistics["rent_ratio_lst"]) {
            this.lineChartStatistics["rent_ratio_lst"] = [];
        }
        if (!this.lineChartStatistics["rental_received_lst"]) {
            this.lineChartStatistics["rental_received_lst"] = [];
        }
        if (!this.lineChartStatistics["rental_receivable_lst"]) {
            this.lineChartStatistics["rental_receivable_lst"] = [];
        }
        // 空置资产列表
        this.outOfRentProperties = useState(useService("estate_big_screen.outOfRentProperties"));

        // 公司名称
        this.companyNM4BigScreen = useState(useService("estate_big_screen.companyName4BigScreenSvc"));

        this.userService = useService("user");
        this.showPropertyDashboard = false;

        onWillStart(async () => {
            this.showPropertyDashboard = await this.userService.hasGroup("estate_big_screen.estate_group_big_screen");
        });
    }

    // 租金单价
    get lineChartDataPriceAVG() {
        return {
            graphType: "line",
            color: "#36A2EB",
            title: "Partner 0",
            values: this.lineChartStatistics["average_price_lst"],
            key: "平均租金单价(元/天/㎡)近12个月走势",
            area: true,
        };
    }
    // 面积出租率
    get lineChartDataRatioRentAreaConventional() {
        return {
            graphType: "line",
            color: "#77bae5",
            title: "Partner 0",
            values: this.lineChartStatistics["rent_ratio_lst"],
            key: "面积出租率(%)近12个月走势",
            area: true,
        };
    }
    // 租金实收
    get lineChartDataRentalReceivedMonth() {
        return {
            graphType: "bar",
            color: "#ffffff",
            opacity: 0.8,
            title: "Partner 0",
            values: this.lineChartStatistics["rental_received_lst"],
            key: "实收月租金(万元)近12个月走势",
            area: true,
        };
    }
    // 租金应收
    get lineChartDataRentalReceivableMonth() {
        return {
            graphType: "line",
            color: "#36A2EB",
            title: "Partner 0",
            values: this.lineChartStatistics["rental_receivable_lst"],
            key: "应收月租金(万元)近12个月走势",
            area: true,
        };
    }

    // 计租面积环形图数据
    get doughnutChtRatioConvAreaQ() {
        // {labels: ['A', 'B', 'C'], values: [30, 50, 20]}
        return {
            labels: ['在租(㎡)', '空置(㎡)'],
            values:
                [this.statistics.pie_chart_ratio_conventional_area_quantity['在租(㎡)'],
                this.statistics.pie_chart_ratio_conventional_area_quantity['空置(㎡)']]
        };
    }
    // 房屋间数环形图数据
    get doughnutChtRatioConvQ() {
        // {labels: ['A', 'B', 'C'], values: [30, 50, 20]}
        return {
            labels: ['在租间数', '空置间数'],
            values:
                [this.statistics.pie_chart_ratio_conventional_quantity['在租间数'],
                this.statistics.pie_chart_ratio_conventional_quantity['空置间数']]
        };
    }

}

registry.category("actions").add("estate_big_screen.estateBigScreen", EstateBigScreen);
