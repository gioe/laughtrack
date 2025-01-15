"use client";

import { z } from "zod";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { showSearchFormSchema } from "./schema";
import { useState } from "react";
import { Navigator } from "../../../objects/class/navigate/Navigator";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "../../../objects/class/params/SearchParamsHelper";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { CityDTO } from "../../../objects/class/city/city.interface";
import { useCityContext } from "@/contexts/CityProvider";
import { Form } from "../ui/form";
import { DropdownFormComponent } from "@/ui/components/dropdown";
import CalendarFormComponent from "@/ui/components/calendar";
import { CircleIconButton } from "@/ui/components/button/circleIcon";
import { Search } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";

export default function ShowSearchBar() {
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
        map.set("city", data.city);
        map.set("from_date", data.dates.from);
        map.set("to_date", data.dates.to);
        paramsHelper.updateParamsFromMap(map);
        navigator.pushPage("show/all", paramsHelper.asParamsString());
        setIsLoading(false);
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(submitForm)}>
                <div
                    className={`flex items-center justify-between w-full max-w-3xl bg-ivory/20 backdrop-blur rounded-full ${styleConfig.searchBorder}`}
                >
                    {/* City Selection Dropdown */}
                    <div className="w-5/12 px-6 py-4 border-r border-gray-600/50">
                        <DropdownFormComponent
                            name="city"
                            placeholder="City"
                            items={selectableCities}
                            form={form}
                        />
                    </div>

                    {/* Date Selection Calendar */}
                    <div className="w-5/12 pl-6 py-4">
                        <CalendarFormComponent name="dates" form={form} />
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
