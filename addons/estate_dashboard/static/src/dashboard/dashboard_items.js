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
        id: "estate_conventional_price_avg",
        description: "在租房屋平均单价（元/天/㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "在租房屋平均单价（元/天/㎡）",
            value: data.conventional_price_avg,
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
        id: "estate_unconventional_price_avg",
        description: "在租林地等平均单价（元/天/㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "在租林地等平均单价（元/天/㎡）",
            value: data.unconventional_price_avg,
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
        id: "estate_property_price_avg",
        description: "在租资产平均单价（元/天/㎡）",
        Component: NumberCard,
        props: (data) => ({
            title: "在租资产平均单价（元/天/㎡）",
            value: data.property_price_avg,
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
        id: "rental_receivable_today",
        description: "当日应收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当日应收（万元）",
            value: Math.round(data.rental_receivable_today / 10000),
        })
    },
    {
        id: "rental_receivable_week",
        description: "当周应收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当周应收（万元）",
            value: Math.round(data.rental_receivable_week / 10000),
        })
    },
    {
        id: "rental_receivable_month",
        description: "当月应收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当月应收（万元）",
            value: Math.round(data.rental_receivable_month / 10000),
        })
    },
    {
        id: "rental_receivable_quarter",
        description: "当季应收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当季应收（万元）",
            value: Math.round(data.rental_receivable_quarter / 10000),
        })
    },
    {
        id: "rental_receivable_year",
        description: "当年应收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当年应收（万元）",
            value: Math.round(data.rental_receivable_year / 10000),
        })
    },
    {
        id: "rental_received_today",
        description: "当日实收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当日实收（万元）",
            value: Math.round(data.rental_received_today / 10000),
        })
    },
    {
        id: "rental_received_week",
        description: "当周实收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当周实收（万元）",
            value: Math.round(data.rental_received_week / 10000),
        })
    },
    {
        id: "rental_received_month",
        description: "当月实收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当月实收（万元）",
            value: Math.round(data.rental_received_month / 10000),
        })
    },
    {
        id: "rental_received_quarter",
        description: "当季实收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当季实收（万元）",
            value: Math.round(data.rental_received_quarter / 10000),
        })
    },
    {
        id: "rental_received_year",
        description: "当年实收（万元）",
        Component: NumberCard,
        props: (data) => ({
            title: "当年实收（万元）",
            value: Math.round(data.rental_received_year / 10000),
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
