/* eslint-disable @typescript-eslint/no-explicit-any */
import { FormSelectable } from "../../../../objects/interface";
import { COMMON_OPTIONS } from "../../../../util/form";
import { SelectComponent } from "../../../select";
import { CheckboxFormComponent } from "../../components/checkbox";
import { DropdownFormComponent } from "../../components/dropdown";

interface ScrapeEntitiesFormBodyProps {
    form: any;
    handleCitySelection: (city: string) => void;
    cityOptions: FormSelectable[];
    clubOptions?: FormSelectable[];
}

export default function ScrapeEntitiesFormBody({
    form,
    handleCitySelection,
    cityOptions,
    clubOptions,
}: ScrapeEntitiesFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <SelectComponent
                placeholder="Select city"
                items={cityOptions}
                handleValueChange={handleCitySelection}
            />
            <CheckboxFormComponent
                name="clubIds"
                form={form}
                items={clubOptions ?? []}
            />
            {clubOptions && (
                <DropdownFormComponent
                    name="headless"
                    title="Headless"
                    form={form}
                    placeholder="Open browser window?"
                    items={COMMON_OPTIONS.YesNo}
                />
            )}
        </div>
    );
}
