/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { getColor, hexToRGBA } from "@web/core/colors/colors";
import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { cookie } from "@web/core/browser/cookie";

export class LineChart extends Component {  // 类名更新为 LineChart
    static template = "estate_big_screen.LineChart";     // 模板名同步更新
    static props = {
        data: { type: Object },
        graphType: { type: String, optional: true },
        className: { type: String, optional: true },
    };
    static defaultProps = {
        graphType: this.props.data.graphType || "line",  // 默认类型设为折线图
    };

    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");
        const chartLoader = useService("chart_loader");
        onWillStart(async () => {
            await chartLoader; // 等待全局加载完成
        });
        // onWillStart(async () => await loadBundle("web.chartjs_lib"));
        useEffect(() => this.renderChart());
    }

    // 保留原有的图表渲染方法（需删除Bar相关逻辑或拆分为单独组件）
    getLineChartConfig() {
        // Add null check for data and values
        if (!this.props.data || !this.props.data.values) {
            return {
                type: this.props.data.graphType || "line",
                data: { labels: [], datasets: [] },
                options: this.getChartOptions()
            };
        }
        const labels = this.props.data.values.map(function (pt) {
            return pt.x;
        });
        const baseOpacity = this.props.data.opacity || 0.9;
        const baseColor = this.props.data.color || getColor(10, cookie.get("color_scheme"));
        const borderColor = this.props.data.is_sample_data ? hexToRGBA(baseColor, 0.1) : baseColor;
        const backgroundColor = this.props.data.is_sample_data
            ? hexToRGBA(baseColor, 0.05)
            : hexToRGBA(baseColor, 0.2);
        return {
            type: this.props.data.graphType || "line",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        borderColor,
                        data: this.props.data.values,
                        fill: this.props.data.area ? "start" : false,
                        label: this.props.data.key,
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: hexToRGBA(borderColor, baseOpacity),
                            font: {
                                size: 20,
                                weight: 'bold'
                            }
                        },
                    },
                    tooltip: {
                        intersect: true,
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: {
                        display: true,
                        ticks: {
                            color: hexToRGBA(borderColor, baseOpacity),
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                    },
                    x: {
                        display: true,
                        ticks: {
                            color: hexToRGBA(borderColor, baseOpacity),
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                    },
                },
                maintainAspectRatio: true,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
            },
        };
    }

    renderChart() {
        if (!this.canvasRef.el) {
            return;
        }

        if (this.chart) {
            this.chart.destroy();
        }
        let config = this.getLineChartConfig();
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

// 注册为独立组件
registry.category("web_components").add("line_chart", LineChart);  // 组件键名更新
