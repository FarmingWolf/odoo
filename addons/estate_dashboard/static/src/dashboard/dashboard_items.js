/** @odoo-module */

import {NumberCard} from "./number_card/number_card";
import {PieChartCard} from "./pie_chart_card/pie_chart_card";
import {registry} from "@web/core/registry";

const items = [
    {
        id: "estate_conventional_quantity",
        description: "房屋间数",
        Component: NumberCard,
        props: (data) => ({
            title: "房屋间数",
            value: data.conventional_cnt,
        })
    },
    {
        id: "estate_conventional_area_quantity",
        description: "房屋计租总面积（㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "房屋计租总面积（㎡）",
            value: data.conventional_area,
        })
    },
    {
        id: "estate_conventional_lease_quantity",
        description: "在租房屋间数",
        Component: NumberCard,
        props: (data) => ({
            title: "在租房屋间数",
            value: data.conventional_cnt_on_rent,
        })
    },
    {
        id: "estate_conventional_area_lease_quantity",
        description: "在租房屋面积（㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "在租房屋面积（㎡）",
            value: data.conventional_area_on_rent,
        })
    },
    {
        id: "ratio_conventional_quantity",
        description: "房屋出租率（间数 %）",
        Component: NumberCard,
        props: (data) => ({
            title: "房屋出租率（间数 %）",
            value: (data.ratio_conventional_cnt * 100).toFixed(1) + '%',
        })
    },
    {
        id: "ratio_conventional_area_quantity",
        description: "房屋面积出租率（%）",
        Component: NumberCard,
        props: (data) => ({
            title: "房屋面积出租率（%）",
            value: (data.ratio_conventional_area * 100).toFixed(1) + '%',
        })
    },
    {
        id: "estate_unconventional_quantity",
        description: "林地等地块数量",
        Component: NumberCard,
        props: (data) => ({
            title: "林地等地块数量",
            value: data.unconventional_cnt,
        })
    },
    {
        id: "estate_unconventional_area_quantity",
        description: "林地等总面积（㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "林地等总面积（㎡）",
            value: data.unconventional_area,
        })
    },
    {
        id: "estate_unconventional_lease_quantity",
        description: "林地等在租地块数量",
        Component: NumberCard,
        props: (data) => ({
            title: "林地等在租地块数量",
            value: data.unconventional_cnt_on_rent,
        })
    },
    {
        id: "estate_unconventional_area_lease_quantity",
        description: "林地等在租面积（㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "林地等在租面积（㎡）",
            value: data.unconventional_area_on_rent,
        })
    },
    {
        id: "ratio_unconventional_quantity",
        description: "林地等地块出租率（地块数量 %）",
        Component: NumberCard,
        props: (data) => ({
            title: "林地等地块出租率（地块数量 %）",
            value: (data.ratio_unconventional_cnt * 100).toFixed(1) + '%',
        })
    },
    {
        id: "ratio_unconventional_area_quantity",
        description: "林地等面积出租率（%）",
        Component: NumberCard,
        props: (data) => ({
            title: "林地等面积出租率（%）",
            value: (data.ratio_unconventional_area * 100).toFixed(1) + '%',
        })
    },
    {
        id: "estate_property_quantity",
        description: "资产总数量（房屋+地块）",
        Component: NumberCard,
        props: (data) => ({
            title: "资产总数量（房屋+地块）",
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
        description: "在租资产数量（房屋+地块）",
        Component: NumberCard,
        props: (data) => ({
            title: "在租资产数量（房屋+地块）",
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
        description: "资产出租率（房屋+地块数量 %）",
        Component: NumberCard,
        props: (data) => ({
            title: "资产出租率（房屋+地块数量 %）",
            value: (data.ratio_property_quantity * 100).toFixed(1) + '%',
        })
    },
    {
        id: "ratio_property_area_quantity",
        description: "总面积出租率（%）",
        Component: NumberCard,
        props: (data) => ({
            title: "总面积出租率（%）",
            value: (data.ratio_property_area_quantity * 100).toFixed(1) + '%',
        })
    },
    {
        id: "pie_chart_ratio_conventional_quantity",
        description: "资产出租、空置对比图（房屋间数）空置率",
        Component: PieChartCard,
        size: 1,
        props: (data) => ({
            title: "资产出租、资产空置对比图（房屋间数）空置率=" + ((1 - data.ratio_conventional_cnt) * 100).toFixed(1) + "%",
            values: data.pie_chart_ratio_conventional_quantity,
        })
    },
    {
        id: "pie_chart_ratio_conventional_area_quantity",
        description: "资产出租、空置对比图（房屋面积）空置率",
        Component: PieChartCard,
        size: 1,
        props: (data) => ({
            title: "资产出租、资产空置对比图（房屋面积）空置率=" + ((1 - data.ratio_conventional_area) * 100).toFixed(1) + "%",
            values: data.pie_chart_ratio_conventional_area_quantity,
        })
    },
    {
        id: "pie_chart_ratio_unconventional_quantity",
        description: "资产出租、空置对比图（地块数量）空置率",
        Component: PieChartCard,
        size: 1,
        props: (data) => ({
            title: "资产出租、资产空置对比图（林地块等）空置率=" + ((1 - data.ratio_unconventional_cnt) * 100).toFixed(1) + "%",
            values: data.pie_chart_ratio_unconventional_quantity,
        })
    },
    {
        id: "pie_chart_ratio_unconventional_area_quantity",
        description: "资产出租、空置对比图（地块面积）空置率",
        Component: PieChartCard,
        size: 1,
        props: (data) => ({
            title: "资产出租、资产空置对比图（地块面积）空置率=" + ((1 - data.ratio_unconventional_area) * 100).toFixed(1) + "%",
            values: data.pie_chart_ratio_unconventional_area_quantity,
        })
    },
    {
        id: "pie_chart_ratio_property_quantity",
        description: "资产出租、空置对比图（总计数量）空置率",
        Component: PieChartCard,
        size: 1,
        props: (data) => ({
            title: "资产出租、资产空置对比图（总计数量）空置率=" + ((1 - data.ratio_property_quantity) * 100).toFixed(1) + "%",
            values: data.pie_chart_ratio_property_quantity,
        })
    },
    {
        id: "pie_chart_ratio_property_area_quantity",
        description: "资产出租、空置对比图（总计面积）空置率",
        Component: PieChartCard,
        size: 1,
        props: (data) => ({
            title: "资产出租、资产空置对比图（总计面积）空置率=" + ((1 - data.ratio_property_area_quantity) * 100).toFixed(1) + "%",
            values: data.pie_chart_ratio_property_area_quantity,
        })
    },
]

items.forEach(item => {
    registry.category("estate_dashboard").add(item.id, item);
});
