"use strict";

import powerbi from "powerbi-visuals-api";
import { FormattingSettingsService } from "powerbi-visuals-utils-formattingmodel";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;

import { VisualFormattingSettingsModel } from "./settings";

export class Visual implements IVisual {
    private target: HTMLElement;
    private updateCount: number;
    private textNode: Text | null = null;
    private formattingSettings: VisualFormattingSettingsModel | null = null; // Initialize as null
    private formattingSettingsService: FormattingSettingsService;

    constructor(options: VisualConstructorOptions) {
        console.log("Visual constructor", options);
        this.formattingSettingsService = new FormattingSettingsService();
        this.target = options.element;
        this.updateCount = 0;

        // Initialize formattingSettings
        this.formattingSettings = new VisualFormattingSettingsModel();

        // Set up initial DOM structure
        const container: HTMLElement = document.createElement("div");
        container.className = "visual";

        const title: HTMLElement = document.createElement("h2");
        title.textContent = "ScaleNow Predictions";

        const predictionParagraph: HTMLElement = document.createElement("p");
        predictionParagraph.id = "prediction";
        predictionParagraph.textContent = "Fetching predictions...";

        container.appendChild(title);
        container.appendChild(predictionParagraph);
        this.target.appendChild(container);
    }

    public update(options: VisualUpdateOptions) {
        if (this.formattingSettings) {
            this.formattingSettings = this.formattingSettingsService.populateFormattingSettingsModel(
                VisualFormattingSettingsModel,
                options.dataViews[0]
            );
        }

        console.log("Visual update", options);
        if (this.textNode) {
            this.textNode.textContent = (this.updateCount++).toString();
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.formattingSettingsService.buildFormattingModel(this.formattingSettings!);
    }
}
