/* eslint-disable @typescript-eslint/no-explicit-any */
import { Selectable } from "../../../objects/interface";
import { COMMON_OPTIONS } from "../../../util/form";
import { CheckboxFormComponent } from "../../checkbox";
import { DropdownFormComponent } from "../../dropdown";
import { SelectComponent } from "../../select";

interface ScrapeEntitiesFormBodyProps {
    form: any;
    handleCitySelection: (city: string) => void;
    cityOptions: Selectable[];
    clubOptions?: Selectable[];
}

export default function ScrapeEntitiesFormBody({
    form,
    handleCitySelection,
    cityOptions,
    clubOptions,
}: ScrapeEntitiesFormBodyProps) {
    return (
        <div className="flex flex-col gap-4 items-center">
            <SelectComponent
                placeholder="Select city"
                items={cityOptions}
                handleValueChange={handleCitySelection}
            />
            <DropdownFormComponent
                name="headless"
                title="Headless"
                form={form}
                placeholder="Leave browser closed?"
                items={COMMON_OPTIONS.YesNo}
            />
            {clubOptions && (
                <CheckboxFormComponent
                    form={form}
                    selectables={clubOptions ?? []}
                />
            )}
        </div>
    );
}
