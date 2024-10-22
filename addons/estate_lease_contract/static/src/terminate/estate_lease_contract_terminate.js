/** @odoo-module */

import {Component, useState} from "@odoo/owl";
import { registry } from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {TodoItem} from "./todo_item";

let todo_list = [
    '已完成租赁房屋回收/验收',
    '已完成注册地址清空和车位归还。终止合同后，系统将自动释放注册地址和车位。',
    '已完成与该商户的资金结算（包括押金、租金等）。终止合同后，系统将不再跟踪本合同的租金支付情况。',
]

export class EstateLeaseContractTerminate extends Component {
    static template = "estate_lease_contract.ContractTerminateAction";
    static components = { TodoItem };

    setup() {
        this.action = useService("action");
        this.terminate_todo_list = useState([]);
        let i = 0;
        for (const todo_c of todo_list) {
            this.terminate_todo_list.push({
                id: i,
                description: todo_c,
                isCompleted: false
            });
            i++;
        }
    }
    toggleTodo(todoId) {
        const todo = this.terminate_todo_list.find((todo) => todo.id === todoId);
        if (todo) {
            todo.isCompleted = !todo.isCompleted;
        }
    }

    removeTodo(todoId) {
        const todoIndex = this.terminate_todo_list.findIndex((todo) => todo.id === todoId);
        if (todoIndex >= 0) {
            this.terminate_todo_list.splice(todoIndex, 1);
        }
    }

    confirm_button_disable(){
        for (const each_todo of this.terminate_todo_list) {
            if (!each_todo.isCompleted) {
                return true;
            }
        }
        return false;
    }

    getURLParams() {
        const urlParams = new URLSearchParams(window.location.hash.substring(1));

        console.log(urlParams);
        console.log(urlParams.get('id'));
        const params = {};

        urlParams.forEach((value, key) => {
            params[key] = value;
        });

        console.log(params);
        console.log(params['id']);
        return params;
    }

    onClickTerminateContract(){
        const params = this.getURLParams();
        console.log(params);
        console.log(params['id']);

        this.action.doAction("estate_lease_contract.estate_lease_contract_terminate_svr_action",
            {additionalContext: params});
    }
}

registry.category("actions").add("estate_lease_contract.contract_terminate_dialog", EstateLeaseContractTerminate);
