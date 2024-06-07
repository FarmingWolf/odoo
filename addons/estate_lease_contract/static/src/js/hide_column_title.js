odoo.define('estate_lease_contract.hide_column_title', ['web'], function (require) {
    "use strict";

    var core = require('web');

    $(document).ready(function () {
        // 使用data-name属性来定位并隐藏表头中的指定列
        $('.o_list_view .o_list_view_header .o_column_title[data-name="state"]').addClass('hidden-title');
    });
});
