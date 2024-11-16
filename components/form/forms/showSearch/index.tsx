"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
    ButtonType,
    RoutePath,
    SortParamValue,
    URLParam,
} from "../../../../objects/enum";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { homeSearchSchema } from "./schema";
import { DropdownFormComponent } from "../../components/dropdown";
import { useState } from "react";
import { Navigator } from "../../../../objects/class/navigate/Navigator";
import { ParamsWrapper } from "../../../../objects/class/params/ParamsWrapper";
import BaseForm from "..";
import CalendarFormComponent from "../../components/calendar";
import { CityInterface } from "../../../../objects/interface/city.interface";

interface HomeSearchFormProps {
    cities: string;
}

export default function ShowSearchForm({ cities }: HomeSearchFormProps) {
    const selectableCities = (JSON.parse(cities) as CityInterface[]).map(
        (city: CityInterface) => {
            return {
                id: city.id,
                name: city.name,
            };
        },
    );

    console.log(selectableCities);

    const [isLoading /*setIsLoading*/] = useState(false);

    ParamsWrapper.updateWithClientParams(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const form = useForm<z.infer<typeof homeSearchSchema>>({
        resolver: zodResolver(homeSearchSchema),
        defaultValues: {
            cityId: "",
            dates: {
                from: undefined,
                to: undefined,
            },
        },
    });

    function submitForm(data: z.infer<typeof homeSearchSchema>) {
        ParamsWrapper.setParamValue(URLParam.City, data.cityId);
        ParamsWrapper.setParamValue(URLParam.StartDate, data.dates.from);
        ParamsWrapper.setParamValue(URLParam.EndDate, data.dates.to);
        ParamsWrapper.setParamValue(URLParam.Sort, SortParamValue.Date);
        navigator.pushPageFromParams(
            RoutePath.ShowSearchResults,
            ParamsWrapper.asParamsString(),
        );
    }

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={
                <div
                    className="flex flex-col lg:flex-row lg:max-w-6xl
        lg:mx-auto items-start justify-center space-x-0 lg:space-x-2
        space-y-4 lg:space-y-0 rounded-lg"
                >
                    <DropdownFormComponent
                        name="cityId"
                        title="City"
                        placeholder="Select your city"
                        items={selectableCities}
                        form={form}
                    />
                    <CalendarFormComponent name="dates" form={form} />
                </div>
            }
            primaryButtonData={{
                type: ButtonType.Submit,
                label: "Search",
                styling: {
                    backgroundColor: "bg-silver-gray",
                },
            }}
        />
    );
}
