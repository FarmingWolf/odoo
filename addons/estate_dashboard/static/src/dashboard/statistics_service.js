/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { reactive } from "@odoo/owl";
import { session } from "@web/session";

export const estateDashboardStatisticsService = {
    dependencies: ["rpc"],
    start(env, { rpc }) {
        const statistics = reactive({ isReady: false });

        async function loadData() {
            // const response = await rpc("/estate_dashboard/statistics", { company_id: companyId });
            const response = await rpc("/estate_dashboard/statistic_super");
            // statisticsByCompany[companyId] = {
            //     // data: response,
            //     // isReady: true
            // };
            // Object.assign(statisticsByCompany[companyId], response, {isReady: true});
            Object.assign(statistics, {isReady: true, data: response });
            console.log(`statisticsByCompany:`, statistics);
            console.log(`statistics长度:`, Object.values(statistics).length);
            console.log(`statistics data:`, statistics.data);
            console.log(`data 长度:`, Object.values(statistics.data).length);
        }
        /** 202408250730 准备将loadData放在dashboard.js中，以下10行是修改前的
        // 将 allowed_companies 转换为数组后进行遍历
        const { user_companies } = session;
        const companiesArray = Object.values(user_companies.allowed_companies);
        // companiesArray.forEach(company => loadData(company.id));
        Promise.all(companiesArray.map(company => loadData(company.id))).then(r => {
            console.log("All statistics loaded:", r);
        }).catch(error => {
            console.error("Error loading some statistics:", error);
        });**/


        /** 202408250730 这个for循环可以用，只是两种方式companyId的取得方式一个需要.id一个不需要
        for (const companyId in user_companies.allowed_companies) {

            console.log(`loadData 开始 companyId ${companyId}`)
            loadData(companyId).then(r => {
                console.log(`loadData 完成 companyId ${companyId}`)
            });
        }**/

        setInterval(loadData, 1000*60*60);
        loadData();
        // loadData().then(r => {
        //     Object.assign(statisticsByCompany, {isReady: true, data: r });
        // });


        // return {
        //     statisticsByCompany,
        //     loadData: loadData
        // };
        return statistics;
    },
};

registry.category("services").add("estate_dashboard.statistics", estateDashboardStatisticsService );
