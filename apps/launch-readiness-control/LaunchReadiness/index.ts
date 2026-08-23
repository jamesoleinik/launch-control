import * as React from "react";

import { DashboardData, loadDashboardData } from "./data";
import { IInputs, IOutputs } from "./generated/ManifestTypes";
import { LaunchReadinessDashboard } from "./LaunchReadinessDashboard";

export class LaunchReadiness implements ComponentFramework.ReactControl<IInputs, IOutputs> {
    private data?: DashboardData;
    private error?: string;
    private loading = false;
    private recordId?: string;
    private refreshVersion = 0;
    private notifyOutputChanged!: () => void;

    public init(
        context: ComponentFramework.Context<IInputs>,
        notifyOutputChanged: () => void,
        _state: ComponentFramework.Dictionary
    ): void {
        this.notifyOutputChanged = notifyOutputChanged;
        context.mode.trackContainerResize(true);
    }

    public updateView(context: ComponentFramework.Context<IInputs>): React.ReactElement {
        const recordId = this.getRecordId(context);
        if (recordId && recordId !== this.recordId) {
            this.recordId = recordId;
            this.load(context, recordId);
        }

        return React.createElement(LaunchReadinessDashboard, {
            data: this.data,
            error: this.error,
            loading: this.loading,
            launchName: context.parameters.launchName.raw ?? "Launch",
            onRefresh: () => {
                if (this.recordId) {
                    this.load(context, this.recordId, true);
                }
            },
        });
    }

    public getOutputs(): IOutputs {
        return {};
    }

    public destroy(): void {
        this.refreshVersion += 1;
    }

    private getRecordId(context: ComponentFramework.Context<IInputs>): string | undefined {
        type ModeWithContext = ComponentFramework.Mode & {
            contextInfo?: { entityId?: string };
        };
        const mode = context.mode as ModeWithContext;
        return mode.contextInfo?.entityId?.replace(/[{}]/g, "");
    }

    private load(
        context: ComponentFramework.Context<IInputs>,
        recordId: string,
        force = false
    ): void {
        if (this.loading && !force) {
            return;
        }
        const requestVersion = ++this.refreshVersion;
        this.loading = true;
        this.error = undefined;
        this.notifyOutputChanged();
        void this.loadData(context, recordId, requestVersion);
    }

    private async loadData(
        context: ComponentFramework.Context<IInputs>,
        recordId: string,
        requestVersion: number
    ): Promise<void> {
        try {
            const data = await loadDashboardData(context.webAPI, recordId);
            if (requestVersion === this.refreshVersion) {
                this.data = data;
            }
        } catch (error: unknown) {
            if (requestVersion === this.refreshVersion) {
                this.error = error instanceof Error
                    ? error.message
                    : "The launch readiness data could not be loaded.";
            }
        } finally {
            if (requestVersion === this.refreshVersion) {
                this.loading = false;
                this.notifyOutputChanged();
            }
        }
    }
}
