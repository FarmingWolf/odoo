odoo.define('estate_lease_contract.CustomMany2manyBinary', ['web.core', 'web.FieldMany2ManyBinary'], function (require) {
    "use strict";

    var webcore = require('web.core');
    const FieldMany2ManyBinary = require('web.FieldMany2ManyBinary');

    const CustomMany2ManyBinary = FieldMany2ManyBinary.extend({
        // 重写初始化方法来添加自定义行为
        init: function () {
            this._super.apply(this, arguments);
            // 可以在这里初始化额外的变量或绑定事件
        },

        // 重写渲染方法来改变布局
        _render: function () {
            this._super.apply(this, arguments);

            // 假设我们想在渲染后通过jQuery来调整样式，这是一个简化的例子
            this.$el.find('.o_field_many2many_binary').addClass('custom-many2many-binary-style');
        },
    });

    webcore.field_registry.add('custom_many2many_binary', CustomMany2ManyBinary);

    return CustomMany2ManyBinary;
});
