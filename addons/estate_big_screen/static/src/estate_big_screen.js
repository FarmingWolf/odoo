/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useEffect, useState} from "@odoo/owl";
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

        this.state = useState({
            showLineCharts: false,
            isFullscreen: false,
            initialized: false
        });

        this.display = {
            controlPanel: false
        };
        this._doughnutCache = useState({})
        this.statistics = useState(useService("estate_big_screen.statistics"));
        this.lineChartStatistics = useState(useService("estate_big_screen.lineChartDataService"));

        // 空置资产列表
        this.outOfRentProperties = useState(useService("estate_big_screen.outOfRentProperties"));

        // 公司名称
        this.companyNM4BigScreen = useState(useService("estate_big_screen.companyName4BigScreenSvc"));

        // 车位车辆信息
        this.parking_spaces_vehicles = useState(useService("estate_big_screen.parkingSpacesVehiclesSvc"));

        this.userService = useService("user");
        this.showPropertyDashboard = false;

        onWillStart(async () => {
            this.showPropertyDashboard = await this.userService.hasGroup("estate_big_screen.estate_group_big_screen");
        });

        useEffect(() => {
            if (!this.state.initialized && this.lineChartStatistics.isReady) {
                this.state.showLineCharts = this.lineChartStatistics.average_price_lst?.length > 0 &&
                    this.lineChartStatistics.rent_ratio_lst?.length > 0 &&
                    this.lineChartStatistics.rental_received_lst?.length > 0 &&
                    this.lineChartStatistics.rental_receivable_lst?.length > 0;

                if (this.state.showLineCharts) {
                    this.state.initialized = true;
                }
            }
        });

        onMounted(async () => {
            console.log("Component onMounted, statistics state:", {
                isReady: this.statistics.isReady,
                data: this.statistics.pie_chart_ratio_conventional_area_quantity
            });
            this.enterFullscreen();
            // 进入页面时隐藏导航栏
            document.querySelector('.o_main_navbar')?.classList.add('d-none');
            document.querySelector('.o_sub_menu')?.classList.add('d-none');
            // 新增移动端触摸控制逻辑
            if (window.innerWidth <= 768) {
                this.setupMobileTouchControls();
            }
        });

        onWillUnmount(() => {
            // 离开页面时恢复导航栏
            document.querySelector('.o_main_navbar')?.classList.remove('d-none');
            document.querySelector('.o_sub_menu')?.classList.remove('d-none');

            document.removeEventListener('fullscreenchange', this.checkFullscreenState);
            document.removeEventListener('webkitfullscreenchange', this.checkFullscreenState);
            document.removeEventListener('msfullscreenchange', this.checkFullscreenState);
        });
    }
    setupMobileTouchControls() {
        const overlay = document.querySelector('.mobile-touch-overlay');
        const scrollContainer = document.querySelector('.dv-full-screen-container');
        let startX, startY;

        overlay?.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, {passive: true});

        overlay?.addEventListener('touchmove', function(e) {
            if (e.target.closest('.mobile-back-button')) return;

            if (!startX || !startY) return;

            const x = e.touches[0].clientX;
            const y = e.touches[0].clientY;

            // 同时处理水平和垂直滚动
            scrollContainer.scrollLeft += startX - x;
            scrollContainer.scrollTop += startY - y;

            startX = x;
            startY = y;
            e.preventDefault();
        }, {passive: false});
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
        // debugger;
        if (!this._doughnutCache) {
            this._doughnutCache = {};
        }

        const cacheKey = 'area_' + this.statistics?.isReady;
        if (this._doughnutCache[cacheKey]) {
            return this._doughnutCache[cacheKey];
        }
        if (!this.statistics?.isReady || !this.statistics?.pie_chart_ratio_conventional_area_quantity) {
            console.log("Statistics not ready:", {
                isReady: this.statistics?.isReady,
                data: this.statistics?.pie_chart_ratio_conventional_area_quantity
            });
            const result = {
                labels: ['在租(㎡)', '空置(㎡)'],
                values: [0, 0],
                isLoading: true
            };
            this._doughnutCache[cacheKey] = result;
            return result;
        }
        console.log("Statistics data loaded:", this.statistics.pie_chart_ratio_conventional_area_quantity);
        const result =  {
            labels: ['在租(㎡)', '空置(㎡)'],
            values:
                [this.statistics.pie_chart_ratio_conventional_area_quantity['在租(㎡)'] || 0,
                this.statistics.pie_chart_ratio_conventional_area_quantity['空置(㎡)'] || 0],
            isLoading: false
        };

        this._doughnutCache[cacheKey] = result;
        return result;
    }
    // 房屋间数环形图数据
    get doughnutChtRatioConvQ() {
        // debugger;
        // {labels: ['A', 'B', 'C'], values: [30, 50, 20]}
        if (!this._doughnutCache) {
            this._doughnutCache = {};
        }

        const cacheKey = 'count_' + this.statistics?.isReady;
        if (this._doughnutCache[cacheKey]) {
            return this._doughnutCache[cacheKey];
        }

        if (!this.statistics?.isReady || !this.statistics?.pie_chart_ratio_conventional_quantity) {
            const result =  {
                labels: ['在租间数', '空置间数'],
                values: [0, 0],
                isLoading: true
            };

            this._doughnutCache[cacheKey] = result;
            return result;
        }
        const result = {
            labels: ['在租间数', '空置间数'],
            values:
                [this.statistics.pie_chart_ratio_conventional_quantity['在租间数'] || 0,
                this.statistics.pie_chart_ratio_conventional_quantity['空置间数'] || 0],
            isLoading: false
        };
        this._doughnutCache[cacheKey] = result;
        return result;

    }
    checkFullscreenState() {
        this.state.isFullscreen = !!(
            document.fullscreenElement ||
            document.webkitFullscreenElement ||
            document.msFullscreenElement
        );
    }

    toggleFullscreen() {
        if (this.state.isFullscreen) {
            this.exitFullscreen();
        } else {
            this.enterFullscreen();
        }
    }

    enterFullscreen() {
        const element = document.documentElement;
        if (element.requestFullscreen) {
            element.requestFullscreen().catch(err => {
                console.error('Error attempting to enable fullscreen:', err);
            });
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen();
        }
    }

    exitFullscreen() {
        if (document.isFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
    goBack() {
        this.exitFullscreen();
        window.history.back();
    }

}

registry.category("actions").add("estate_big_screen.estateBigScreen", EstateBigScreen);
