/** @odoo-module */

import { NumberCard } from "./number_card/number_card";
import { PieChartCard } from "./pie_chart_card/pie_chart_card";
import { registry } from "@web/core/registry";

const items = [
    {
        id: "estate_property_quantity",
        description: "资产总数量（房屋间数）",
        Component: NumberCard,
        props: (data) => ({
            title: "资产总数量（房屋间数）",
            value: data.estate_property_quantity,
        })
    },
    {
        id: "estate_property_area_quantity",
        description: "资产计租总面积（㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "计租总面积（㎡）",
            value: data.estate_property_area_quantity,
        })
    },
    {
        id: "estate_property_lease_quantity",
        description: "在租资产数量（房屋间数）",
        Component: NumberCard,
        props: (data) => ({
            title: "在租资产数量（房屋间数）",
            value: data.estate_property_lease_quantity,
        })
    },
    {
        id: "estate_property_area_lease_quantity",
        description: "在租资产面积（㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "在租资产面积（㎡）",
            value: data.estate_property_area_lease_quantity,
        })
    },
    {
        id: "ratio_property_quantity",
        description: "资产出租率（房屋间数 %）",
        Component: NumberCard,
        props: (data) => ({
            title: "资产出租率（房屋间数 %）",
            value: data.ratio_property_quantity,
        })
    },
    {
        id: "ratio_property_area_quantity",
        description: "资产面积出租率（%）",
        Component: NumberCard,
        props: (data) => ({
            title: "资产面积出租率（%）",
            value: data.ratio_property_area_quantity,
        })
    },
    {
        id: "pie_chart_ratio_property_quantity",
        description: "资产出租、空置对比图（房屋间数）",
        Component: PieChartCard,
        size: 2,
        props: (data) => ({
            title: "资产出租、空置对比图（房屋间数）",
            values: data.pie_chart_ratio_property_quantity,
        })
    },
    {
        id: "pie_chart_ratio_property_area_quantity",
        description: "资产出租、空置对比图（㎡）",
        Component: PieChartCard,
        size: 2,
        props: (data) => ({
            title: "资产出租、空置对比图（㎡）",
            values: data.pie_chart_ratio_property_area_quantity,
        })
    },
]

items.forEach(item => {
    registry.category("estate_dashboard").add(item.id, item);
});
