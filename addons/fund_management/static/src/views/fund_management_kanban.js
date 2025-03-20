/** @odoo-module */

import { registry } from '@web/core/registry';

import { FundManagementDashboard } from '../components/fund_management_dashboard';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import {FundManagementDocumentDropZone, FundManagementDocumentUpload} from "../mixins/document_upload";
import {FundManagementMobileQRCode} from "../mixins/qrcode";

export class FundManagementKanbanController extends FundManagementDocumentUpload(KanbanController) {}

export class FundManagementKanbanRenderer extends FundManagementDocumentDropZone(FundManagementMobileQRCode(KanbanRenderer)) {}
FundManagementKanbanRenderer.template = 'fund_management.KanbanRenderer';

export class FundManagementDashboardKanbanRenderer extends FundManagementKanbanRenderer {}
FundManagementDashboardKanbanRenderer.components = { ...FundManagementDashboardKanbanRenderer.components, FundManagementDashboard};
FundManagementDashboardKanbanRenderer.template = 'fund_management.DashboardKanbanRenderer';

registry.category('views').add('fund_management_kanban', {
    ...kanbanView,
    buttonTemplate: 'fund_management.KanbanButtons',
    Controller: FundManagementKanbanController,
    Renderer: FundManagementKanbanRenderer,
});

registry.category('views').add('fund_management_dashboard_kanban', {
    ...kanbanView,
    buttonTemplate: 'fund_management.KanbanButtons',
    Controller: FundManagementKanbanController,
    Renderer: FundManagementDashboardKanbanRenderer,
});
