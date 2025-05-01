/** @odoo-module **/

import { Component, onMounted, onWillStart, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

export class DoughnutChart extends Component {
    static template = "estate_big_screen.DoughnutChart";
    static props = {
        data: { type: Object },
        centerText: { type: String, optional: true },
        cutout: { type: String, optional: true },
        colors: { type: Array, optional: true }
    };

    setup() {
        const chartLoader = useService("chart_loader");
        onWillStart(async () => {
            await chartLoader; // 等待全局加载完成
        });
        this.chart = null;
        this.canvasRef = useRef("canvas");

        // 加载Chart.js库
        onMounted(async () => {
            if (this.props.data) {
                this.renderChart();
            }
        });
    }

    // 获取默认颜色（当未传入colors时使用）
    getDefaultColors(opacity = 0.7) {
        const colors = [
        "#36A2EB", "#165e83", "#9966FF", "#FF9F40", "#9370DB", "#FF6384", "#32CD32",
        "#8A2BE2", "#7CFC00", "#FF4500", "#20B2AA", "#FFCE56", "#4BC0C0"
        ];

        return colors.map(color => {
            // 将 HEX 转换为 RGBA
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${opacity})`;
        });
    }

    // 生成图表配置
    getChartConfig(opacity = 0.7) {
        return {
            type: "doughnut",
            data: {
                labels: this.props.data.labels,
                datasets: [{
                    data: this.props.data.values,
                    backgroundColor: this.props.colors || this.getDefaultColors(opacity),
                    borderWidth: 0,
                }]
            },
            options: {
                cutout: this.props.cutout || "60%",
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false,
                        text: this.props.title,
                        padding: 4,
                        color: "#FFFFFF",
                        font : {
                            size: 14,
                            weight: "bold"
                        }

                    },
                    legend: {
                        display: true,
                        position: "top",
                        labels: {
                            color: "#FFFFFF",
                            font: { weight: "bold" },
                        }
                    },
                    tooltip: {
                        bodyFont: { weight: "bold" }
                    }
                }
            }
        };
    }

    // 渲染图表
    renderChart() {
        if (!this.canvasRef.el) {
            return;
        }

        if (this.chart) {
            this.chart.destroy();
        }
        const opacity = 0.7;
        this.chart = new Chart(
            this.canvasRef.el,
            this.getChartConfig(opacity)
        );
    }
}

// 注册为全局组件
registry.category("web_components").add("doughnut_chart", DoughnutChart);
