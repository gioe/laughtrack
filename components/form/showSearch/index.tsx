"use client";

import { Form } from "../../ui/form";
import ShowSearchFormBody from "./body";
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
import { Selectable } from "../../../objects/interface";

interface ShowSearchFormProps {
    cities: string;
}
export default function ShowSearchForm({ cities }: ShowSearchFormProps) {
    const parsedCities = JSON.parse(cities) as CityDTO[];

    const [isLoading, setIsLoading] = useState(false);

    const selectableCities = parsedCities.map((city: CityDTO) => {
        return {
            id: city.id,
            value: city.name,
            displayName: city.name,
        };
    }) as Selectable[];

    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

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

    function submitForm(data: z.infer<typeof showSearchFormSchema>) {
        setIsLoading(true);
        const map = new Map<URLParam, ParamsDictValue>();

        map.set("city", data.city);
        map.set("from_date", data.dates.from);
        map.set("to_date", data.dates.to);

        paramsHelper.updateParamsFromMap(map);
        navigator.pushPage("show/all", paramsHelper.asParamsString());
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(submitForm)}>
                <ShowSearchFormBody
                    items={selectableCities}
                    form={form}
                    isLoading={isLoading}
                />
            </form>
        </Form>
    );
}
