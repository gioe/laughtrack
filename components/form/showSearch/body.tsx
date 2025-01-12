/* eslint-disable @typescript-eslint/no-explicit-any */
import { CircleIconButton } from "@/components/button/circleIcon";
import { Selectable } from "../../../objects/interface";
import CalendarFormComponent from "../../calendar";
import { DropdownFormComponent } from "../../dropdown";
import { Search } from "lucide-react";

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
        <div className="flex items-center w-full max-w-3xl bg-white/20 backdrop-blur rounded-full">
            <div className="flex-1 flex items-center px-6 border-r border-gray-600/50 m-4">
                <DropdownFormComponent
                    name="city"
                    placeholder="City"
                    items={items}
                    form={form}
                />
            </div>

            <div className="flex-1 flex items-center px-6">
                <CalendarFormComponent name="dates" form={form} />
            </div>
            <CircleIconButton>
                <Search className="w-5 h-5 text-white" />
            </CircleIconButton>
        </div>
    );
}
