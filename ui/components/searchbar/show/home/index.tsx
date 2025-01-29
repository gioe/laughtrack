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
import { Loader2 } from "lucide-react";
import CalendarComponent from "@/ui/components/calendar";

const LoadingOverlay = () => (
    <div className="absolute inset-0 bg-black/20 backdrop-blur-sm rounded-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-white animate-spin" />
    </div>
);

export default function ShowSearchForm() {
    const cityList = useCityContext();
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
                from: undefined,
                to: undefined,
            },
        },
    });

    async function submitForm(data: z.infer<typeof showSearchFormSchema>) {
        try {
            setIsLoading(true);
            const map = new Map<URLParam, ParamsDictValue>();
            map.set(QueryProperty.City, data.city);
            map.set(QueryProperty.FromDate, data.dates.from);
            map.set(QueryProperty.ToDate, data.dates.to);

            await new Promise((resolve) => setTimeout(resolve, 300));

            paramsHelper.updateParamsFromMap(map);
            navigator.pushPage("show/all", paramsHelper.asParamsString());
        } catch (error) {
            console.error("Error during navigation:", error);
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(submitForm)} className="relative">
                <div className="flex flex-col md:flex-row items-stretch md:items-center bg-ivory/20 backdrop-blur rounded-2xl md:rounded-full overflow-hidden">
                    {isLoading && <LoadingOverlay />}

                    <div className="flex-1 min-w-0 md:min-w-[240px] border-b md:border-b-0 md:border-r border-gray-600/30">
                        <div className="px-4 md:px-8 py-4">
                            <DropdownComponent
                                icon={
                                    <MapPin className="w-5 h-5 text-white/80" />
                                }
                                name="city"
                                placeholder="Where"
                                items={selectableCities}
                                form={form}
                                className="w-full bg-transparent text-lg md:text-xl text-white ring-transparent focus:ring-transparent 
                                shadow-none border-transparent focus:outline-none outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex-1 min-w-0 md:min-w-[240px]">
                        <div className="px-4 md:px-8 py-4">
                            <CalendarComponent
                                variant="form"
                                name="dates"
                                form={form}
                                placeholder="When"
                                className="w-full bg-transparent text-lg md:text-xl text-white focus:outline-none"
                                icon={
                                    <Calendar className="w-5 h-5 text-white/80" />
                                }
                                chevrons={
                                    <ChevronsUpDown className="w-5 h-5 text-white/50" />
                                }
                                textSize="text-xl"
                            />
                        </div>
                    </div>

                    <div className="px-4 md:px-6 py-4 md:py-0 flex justify-center md:justify-start">
                        <CircleIconButton
                            type="submit"
                            isLoading={isLoading}
                            className="bg-copper w-full md:w-auto"
                        >
                            <Search className="w-5 h-5 text-white" />
                        </CircleIconButton>
                    </div>
                </div>
            </form>
        </Form>
    );
}
