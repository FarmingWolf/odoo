/** @odoo-module **/

import {Component, onMounted, onWillUnmount, useEffect, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {sharedState} from "./shared_info";

/**
 * 工具函数：提取原始值（支持 ref / promise / function）
 */
function getRawValue(value) {
    if (value && typeof value === 'object' && 'value' in value) {
        return value.value;
    }
    return value;
}

export class ScrollingDataGrid extends Component {
    static template = "estate_big_screen.ScrollingDataGrid";
    static props = {
        data: { type: [Array, Object, Function, Promise], optional: false },
        interval: { type: Number, optional: true },
        fadeDuration: { type: Number, optional: true },
        visibleRows: { type: Number, optional: true },
        rowHeight: { type: Number, optional: true },
        no_data_label: { type: String, optional: true },
    };
    static defaultProps = {
        interval: 5000,
        fadeDuration: 500,
        visibleRows: 5,
        rowHeight: 40,
        no_data_label: "暂无数据",
    };

    setup() {
        this.state = useState({
            currentIndex: 0,
            isTransitioning: false,
            headers: [],
            isLoading: true,
            error: null,
            displayData: [],
            currentDisplayData: [],
            rowClasses: [],
            info4Show: null,
            sharedState: sharedState,
        });

        this.timer = null;

        // 初次加载或 data 引用变化时触发
        useEffect(() => {
            this.loadData().then(() => {
                this.updateRowClasses();
                this.updateCurrentDisplayData();
                this.startRotation();
            });
        }, () => [this.props.data]);

        // 当 isReady 变为 true 时重新加载
        useEffect(() => {
            const rawData = getRawValue(this.props.data);
            if (rawData?.isReady) {
                this.loadData().then(() => {
                    this.updateRowClasses();
                    this.updateCurrentDisplayData();
                    this.startRotation();
                });
            }
        }, () => [this.props.data.isReady]);

        onMounted(() => {
            if (!this.state.isLoading && !this.state.error) {
                this.startRotation();
            }
        });

        onWillUnmount(() => {
            this.stopRotation();
        });
    }

    /**
     * 获取 record 的内层对象
     */
    getInnerRecord(record) {
        const values = Object.values(record);
        return values.length > 0 ? values[0] : {};
    }

    updateRowClasses() {
        const visibleRows = this.props.visibleRows;
        this.state.rowClasses = Array.from({ length: visibleRows }, (_, i) =>
            i % 2 === 0 ? "even-row" : "odd-row"
        );
    }

    updateCurrentDisplayData() {
        const start = this.state.currentIndex;
        const end = Math.min(start + this.props.visibleRows, this.state.displayData.length);
        this.state.currentDisplayData = this.state.displayData.slice(start, end);
        this.updateRowClasses();
    }

    async loadData() {
        try {
            this.state.isLoading = true;
            this.state.error = null;

            const rawData = getRawValue(this.props.data);

            if (!rawData?.isReady) {
                return; // 未准备好时不处理
            }

            let dataToRender = rawData.data || [];
            const validData = Array.isArray(dataToRender) ? dataToRender : [];

            this.state.displayData = validData;

            // 提取表头
            if (validData.length > 0) {
                const innerObj = this.getInnerRecord(validData[0]);
                this.state.headers = Object.keys(innerObj);
            } else {
                this.state.headers = [];
            }

        } catch (error) {
            console.error("Failed to load data:", error);
            this.state.error = error;
            this.state.displayData = [];
            this.state.headers = [];
        } finally {
            this.state.isLoading = false;
        }
    }

    startRotation() {
        this.stopRotation();
        if (!this.state.isHovered && this.state.displayData.length > 0) {
            this.timer = setInterval(() => {
                this.transitionData();
            }, this.props.interval);
        }
    }

    stopRotation() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    transitionData() {
        if (this.state.isTransitioning || this.state.isHovered || this.state.displayData.length === 0) return;

        this.state.isTransitioning = true;

        setTimeout(() => {
            const nextIndex = this.state.currentIndex + this.props.visibleRows;
            this.state.currentIndex = nextIndex >= this.state.displayData.length ? 0 : nextIndex;
            this.updateCurrentDisplayData();
            let end_idx = this.state.currentIndex + this.props.visibleRows
            if (end_idx > this.state.displayData.length) {
                end_idx = this.state.displayData.length
            }
            this.state.info4Show = "（" + (this.state.currentIndex + 1) + "—" + end_idx + "）/ " + this.state.displayData.length;
            this.state.sharedState.out_of_rent_p_info_show = this.state.info4Show;

            setTimeout(() => {
                this.state.isTransitioning = false;
            }, this.props.fadeDuration);
        }, this.props.fadeDuration);
    }

    handleMouseEnter() {
        this.state.isHovered = true;
        this.stopRotation();
    }

    handleMouseLeave() {
        this.state.isHovered = false;
        this.startRotation();
    }

    getContainerStyle() {
        return `
            --fade-duration: ${this.props.fadeDuration}ms;
            --row-height: ${this.props.rowHeight}px;
            height: ${(this.props.visibleRows + 1) * this.props.rowHeight}px;
            position: absolute;
        `;
    }
}

registry.category("web_components").add("scrolling_datagrid", ScrollingDataGrid);