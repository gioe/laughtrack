/* eslint-disable @typescript-eslint/no-explicit-any */
import { Selectable } from "../../../objects/interface";
import { FullRoundedButton } from "../../button/rounded/full";
import CalendarFormComponent from "../../calendar";
import { DropdownFormComponent } from "../../dropdown";

interface ShowSearchFormBodyProps {
    items: Selectable[];
    form: any;
    isLoading: boolean;
}

export default function ShowSearchFormBody({
    items,
    form,
    isLoading,
}: ShowSearchFormBodyProps) {
    return (
        <div
            className="flex flex-col justify-center
            lg:flex-row lg:max-w-5xl lg:mx-auto lg:space-x-5 lg:h-40"
        >
            <div className="h-20">
                <DropdownFormComponent
                    name="city"
                    placeholder="City"
                    items={items}
                    form={form}
                />
            </div>

            <div className="h-20 hover:cursor-pointer">
                <CalendarFormComponent name="dates" form={form} />
            </div>
            <div className="h-10 mt-1">
                <FullRoundedButton label="Search" isLoading={isLoading} />
            </div>
        </div>
    );
}
