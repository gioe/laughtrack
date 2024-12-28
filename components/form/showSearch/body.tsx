/* eslint-disable @typescript-eslint/no-explicit-any */
import { Selectable } from "../../../objects/interface";
import { FormButton } from "../../button/form/home";
import CalendarFormComponent from "../../calendar";
import { DropdownFormComponent } from "../../dropdown";

interface ShowSearchFormBodyProps {
    items: Selectable[];
    form: any;
}

export default function ShowSearchFormBody({
    items,
    form,
}: ShowSearchFormBodyProps) {
    return (
        <div
            className="flex flex-col space-y-4 
            lg:flex-row lg:max-w-6xl lg:mx-auto lg:space-x-2"
        >
            <DropdownFormComponent
                name="city"
                title="City"
                placeholder="Select your city"
                items={items}
                form={form}
            />
            <CalendarFormComponent name="dates" form={form} />
            <FormButton label="Search" />
        </div>
    );
}
