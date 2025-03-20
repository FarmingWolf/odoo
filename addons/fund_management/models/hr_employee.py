# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _group_hr_fund_management_user_domain(self):
        # We return the domain only if the group exists for the following reason:
        # When a group is created (at module installation), the `res.users` form view is
        # automatically modified to add application accesses. When modifying the view, it
        # reads the related field `fund_management_manager_id` of `res.users` and retrieve its domain.
        # This is a problem because the `group_fund_management_user` record has already been created but
        # not its associated `ir.model.data` which makes `self.env.ref(...)` fail.
        group = self.env.ref('fund_management.group_fund_management_team_approver', raise_if_not_found=False)
        return [('groups_id', 'in', group.ids)] if group else []

    fund_management_manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Fund Management',
        compute='_compute_fund_management_manager', store=True, readonly=False,
        domain=_group_hr_fund_management_user_domain,
        help='Select the user responsible for approving "Fund Management" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).',
    )

    filter_for_fund_management = fields.Boolean(store=False, search='_search_filter_for_fund_management')

    @api.depends('parent_id')
    def _compute_fund_management_manager(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            manager = employee.parent_id.user_id
            if manager and manager.has_group('fund_management.group_fund_management_user') \
                    and (employee.fund_management_manager_id == previous_manager or not employee.fund_management_manager_id):
                employee.fund_management_manager_id = manager
            elif not employee.fund_management_manager_id:
                employee.fund_management_manager_id = False

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['fund_management_manager_id']

    def _search_filter_for_fund_management(self, operator, value):
        assert operator == '='
        assert value

        res = [('id', '=', 0)]  # Nothing accepted by domain, by default
        if self.user_has_groups('fund_management.group_fund_management_user') or self.user_has_groups('account.group_account_user'):
            res = ['|', ('company_id', '=', False), ('company_id', 'child_of', self.env.company.root_id.id)]  # Then, domain accepts everything
        elif self.user_has_groups('fund_management.group_fund_management_team_approver') and self.env.user.employee_ids:
            user = self.env.user
            employee = self.env.user.employee_id
            res = [
                '|', '|', '|',
                ('department_id.manager_id', '=', employee.id),
                ('parent_id', '=', employee.id),
                ('id', '=', employee.id),
                ('fund_management_manager_id', '=', user.id),
                '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ]
        elif self.env.user.employee_id:
            employee = self.env.user.employee_id
            res = [('id', '=', employee.id), '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)]
        return res


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    fund_management_manager_id = fields.Many2one('res.users', readonly=True)


class User(models.Model):
    _inherit = ['res.users']

    fund_management_manager_id = fields.Many2one(related='employee_id.fund_management_manager_id', readonly=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['fund_management_manager_id']
