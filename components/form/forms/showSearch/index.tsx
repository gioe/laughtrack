"use client";

import BaseForm from "..";
import ShowSearchFormBody from "./body";
import { z } from "zod";
import { FormDirection, RoutePath } from "../../../../objects/enum";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { showSearchFormSchema } from "./schema";
import { useState } from "react";
import { Navigator } from "../../../../objects/class/navigate/Navigator";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "../../../../objects/class/params/SearchParamsHelper";
import { FormButton } from "../../components/button/home";
import { useCityContext } from "../../../../contexts/CityContext";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

export default function ShowSearchForm() {
    const { cities } = useCityContext();
    const readOnlySearchParams = useSearchParams();

    const [isLoading, setIsLoading] = useState(false);

    const searchParams = new URLSearchParams(readOnlySearchParams);
    const paramsHelper = new SearchParamsHelper(searchParams);
    const navigator = new Navigator(usePathname(), useRouter());

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

    function submitForm(data: z.infer<typeof showSearchFormSchema>) {
        setIsLoading(true);
        const map = new Map<URLParam, ParamsDictValue>();

        map.set("city", data.city);
        map.set("from_date", data.dates.from);
        map.set("to_date", data.dates.to);

        paramsHelper.updateParamsFromMap(map);
        navigator.pushPageFromParams(
            RoutePath.ShowSearch,
            paramsHelper.asParamsString(),
        );
    }

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            direction={FormDirection.Horizontal}
            body={<ShowSearchFormBody items={cities} form={form} />}
            primaryButton={<FormButton label="Search" />}
        />
    );
}
