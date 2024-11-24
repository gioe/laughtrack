/* eslint-disable @typescript-eslint/no-explicit-any */
import { SelectableItem } from "../../../../objects/interface";
import CalendarFormComponent from "../../components/calendar";
import { DropdownFormComponent } from "../../components/dropdown";

interface ShowSearchFormBodyProps {
    items: SelectableItem[];
    form: any;
}

export default function ShowSearchFormBody({
    items,
    form,
}: ShowSearchFormBodyProps) {
    return (
        <div className="flex flex-col lg:flex-row lg:max-w-6xl lg:mx-auto items-start justify-center lg:space-x-2 space-y-4 lg:space-y-0 rounded-lg">
            <DropdownFormComponent
                name="city"
                title="City"
                placeholder="Select your city"
                items={items}
                form={form}
            />
            <CalendarFormComponent name="dates" form={form} />
        </div>
    );
}
