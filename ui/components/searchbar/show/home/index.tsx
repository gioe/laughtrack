"use client";

import CalendarFormComponent from "@/ui/components/calendar";
import { z } from "zod";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Navigator } from "../../../../../objects/class/navigate/Navigator";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "../../../../../objects/class/params/SearchParamsHelper";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useCityContext } from "@/contexts/CityProvider";
import { Form } from "../../../ui/form";
import { DropdownComponent } from "@/ui/components/dropdown";
import { CircleIconButton } from "@/ui/components/button/circleIcon";
import { Calendar, ChevronsUpDown, MapPin, Search } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { CityDTO } from "@/lib/data/cities/getCities";
import { showSearchFormSchema } from "./schema";
import { QueryProperty } from "@/objects/enum";

export default function ShowSearchForm() {
    const cityList = useCityContext();
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const [isLoading, setIsLoading] = useState(false);

    const selectableCities = cityList.cities.map((city: CityDTO) => ({
        id: city.id,
        value: city.name,
        display: city.name,
    }));

    const form = useForm<z.infer<typeof showSearchFormSchema>>({
        resolver: zodResolver(showSearchFormSchema),
        defaultValues: {
            city: undefined,
            dates: {
                from: new Date(),
                to: new Date(),
            },
        },
    });

    async function submitForm(data: z.infer<typeof showSearchFormSchema>) {
        setIsLoading(true);
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.City, data.city);
        map.set(QueryProperty.FromDate, data.dates.from);
        map.set(QueryProperty.ToDate, data.dates.to);
        paramsHelper.updateParamsFromMap(map);
        navigator.pushPage("show/all", paramsHelper.asParamsString());
        setIsLoading(false);
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(submitForm)}>
                <div
                    className={`flex items-center justify-between w-full max-w-3xl bg-ivory/20 backdrop-blur rounded-full`}
                >
                    {/* City Selection Dropdown */}
                    <div className="w-5/12 px-6 py-4 border-r border-gray-600/50">
                        <DropdownComponent
                            icon={
                                <MapPin
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                            }
                            name="city"
                            placeholder="City"
                            items={selectableCities}
                            form={form}
                            className={`text-[20px] text-white rounded-lg font-dmSams ring-transparent focus:ring-transparent 
                                shadow-none border-transparent focus:outline-none outline-none`}
                        />
                    </div>

                    {/* Date Selection Calendar */}
                    <div className="w-5/12 pl-6 py-4">
                        <CalendarFormComponent
                            name="dates"
                            form={form}
                            className={`text-[20px] text-white rounded-lg px-3 ring-transparent 
                                focus:ring-transparent border-transparent focus:outline-none outline-none`}
                            icon={
                                <Calendar
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                            }
                            chevrons={
                                <ChevronsUpDown
                                    className={`w-5 h-5 ${styleConfig.iconTextColor} pl-2`}
                                    style={{ opacity: 0.5 }}
                                />
                            }
                            textSize="text-[20px]"
                        />
                    </div>

                    {/* Search Button */}
                    <div className="w-2/12 flex justify-center">
                        <CircleIconButton type="submit">
                            <Search
                                className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                            />
                        </CircleIconButton>
                    </div>
                </div>
            </form>
        </Form>
    );
}
