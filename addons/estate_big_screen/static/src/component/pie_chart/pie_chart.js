/** @odoo-module */

import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";
import {Component, onWillStart, useRef, onMounted, onWillUnmount, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PieChart extends Component {
    static template = "estate_big_screen.PieChart";
    static props = {
        label: { type: String, optional: true },
        data: { type: Object, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;

        const chartLoader = useService("chart_loader");
        onWillStart(async () => {
            // await loadJS(["/web/static/lib/Chart/Chart.js"]);
            await chartLoader; // 等待全局加载完成
            this.chartLoaded = true;
        });

        onMounted(() => {
            if (this.props.data) {
                this.renderChart();
            }
        });
        useEffect(
            () => {
                if (this.chart) {
                    this.chart.destroy();
                }
                this.renderChart();
            },
            () => [this.props.data ? JSON.stringify(this.props.data) : null]
            );

        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
            }
        });

    }

    async renderChart() {
        // Check if data exists and is valid
        if (!this.props.data || typeof this.props.data !== 'object') {
            return;
        }

        // Wait for Chart.js to be loaded
        if (!window.Chart) {
            await new Promise(resolve => {
                const check = () => {
                    if (window.Chart) {
                        resolve();
                    } else {
                        setTimeout(check, 50);
                    }
                };
                check();
            });
        }

        const labels = Object.keys(this.props.data);
        const data = Object.values(this.props.data);
        // Don't render if no valid data
        if (labels.length === 0 || data.length === 0) {
            return;
        }
        const color = labels.map((_, index) => getColor(index));
        if (this.chart) {
            this.chart.destroy();
        }
        this.chart = new Chart(this.canvasRef.el, {
            type: "pie",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: this.props.label || '',
                        data: data,
                        backgroundColor: color,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: {
                        labels: {
                            color: 'white', // Set legend labels to white
                            font: {
                                size: 14 // Optional: adjust font size
                            }
                        }
                    }
                }
            }
        });
    }
}