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

export default function ShowSearchBarProps() {
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
                from: new Date(),
                to: new Date(),
            },
        },
    });

    async function submitForm(data: z.infer<typeof showSearchFormSchema>) {
        try {
            setIsLoading(true);
            const map = new Map<URLParam, ParamsDictValue>();
            map.set("city", data.city);
            map.set("from_date", data.dates.from);
            map.set("to_date", data.dates.to);

            navigator.pushPage("show/all", paramsHelper.asParamsString());
        } catch (error) {
            // Handle error appropriately
            console.error("Form submission failed:", error);
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(submitForm)}>
                <div className="flex items-center w-full max-w-3xl bg-white/20 backdrop-blur rounded-full">
                    <div className="flex-1 flex items-center px-6 border-r border-gray-600/50 m-4">
                        <DropdownFormComponent
                            name="city"
                            placeholder="City"
                            items={selectableCities}
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
            </form>
        </Form>
    );
}
