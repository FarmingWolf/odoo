/** @odoo-module */

import { Component } from "@odoo/owl";
import { PieChart } from "../pie_chart/pie_chart";

export class PieChartCard extends Component {
    static template = "estate_big_screen.PieChartCard";
    static components = { PieChart }
    static props = {
        title: {
            type: String,
        },
        title2: {
            type: String,
        },
        values: {
            type: Object,
        },
    }
}