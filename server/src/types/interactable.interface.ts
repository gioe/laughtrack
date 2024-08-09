import { ClickOptions, ElementHandle, NodeFor, WaitForSelectorOptions } from "puppeteer";

export default interface Interactable {
    select(selector: string, ...values: string[]): Promise<string[]>;
    click(selector: string, options?: Readonly<ClickOptions>): Promise<void>;
    waitForSelector<Selector extends string>(selector: Selector, options?: WaitForSelectorOptions): Promise<ElementHandle<NodeFor<Selector>> | null>;
}

