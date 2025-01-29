import React from "react";
import { Calendar, MapPin, Search, ChevronsUpDown } from "lucide-react";
import { Form, UseFormReturn } from "react-hook-form";
import CalendarComponent from "@/ui/components/calendar";
import DropdownComponent from "@/ui/components/dropdown";
import { Selectable } from "@/objects/interface";
import { CircleIconButton } from "@/ui/components/button/circleIcon";

interface SearchBarProps {
    form: UseFormReturn<any>;
    cities: Selectable[];
    onSubmit: (data: any) => void;
    isLoading?: boolean;
}

const SearchBar = ({
    form,
    cities,
    onSubmit,
    isLoading = false,
}: SearchBarProps) => {
    return (
        <Form {...form}>
            <div className="w-full max-w-6xl mx-auto px-4">
                <form
                    onSubmit={form.handleSubmit(onSubmit)}
                    className="relative"
                >
                    <div className="flex items-center bg-black/30 backdrop-blur rounded-full overflow-hidden">
                        {/* City Selection */}
                        <div className="flex-1 min-w-[240px] border-r border-gray-600/30">
                            <DropdownComponent
                                icon={
                                    <MapPin className="w-5 h-5 text-white/80" />
                                }
                                name="city"
                                placeholder="Where"
                                items={cities}
                                form={form}
                                className="w-full bg-transparent text-xl text-white p-4 focus:outline-none"
                            />
                        </div>

                        {/* Date Selection */}
                        <div className="flex-1 min-w-[240px]">
                            <CalendarComponent
                                name="dates"
                                form={form}
                                placeholder="When"
                                className="w-full bg-transparent text-xl text-white p-4 focus:outline-none"
                                icon={
                                    <Calendar className="w-5 h-5 text-white/80" />
                                }
                                chevrons={
                                    <ChevronsUpDown className="w-5 h-5 text-white/50" />
                                }
                                textSize="text-xl"
                            />
                        </div>

                        {/* Search Button */}
                        <div className="px-2">
                            <CircleIconButton
                                type="submit"
                                isLoading={isLoading}
                                className="bg-amber-600 hover:bg-amber-500"
                            >
                                <Search className="w-5 h-5 text-white" />
                            </CircleIconButton>
                        </div>
                    </div>
                </form>
            </div>
        </Form>
    );
};

export default SearchBar;
