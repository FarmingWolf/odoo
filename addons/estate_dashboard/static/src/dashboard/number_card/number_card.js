/** @odoo-module */

import { Component } from "@odoo/owl";

export class NumberCard extends Component {
    static template = "estate_dashboard.NumberCard";
    static props = {
        title: {
            type: String,
        },
        value: {
            type: Number,
        }
    }
}