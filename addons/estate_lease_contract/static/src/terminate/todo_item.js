/** @odoo-module */

import { Component } from "@odoo/owl";

export class TodoItem extends Component {
    static template = "estate_lease_contract.TodoItem";
    static props = {
        todo: {
            type: Object,
            shape: { id: Number, description: String, isCompleted: Boolean }
        },
        toggleState: Function,
        removeTodo: Function,
    };

    onChange() {
        this.props.toggleState(this.props.todo.id);
    }

}
