"use client";

import { useForm } from "react-hook-form";
import { Button } from "../../ui/button";
import { Form } from "../../ui/form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { URLParam } from "../../../util/enum";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { DropdownFormComponent } from "../../formComponents/dropdown";
import CalendarFormComponent from "../../formComponents/calendar";
import { homeSearchSchema } from "./schema";
import { FormSelectable } from "../../../objects/interfaces";
import { LaughtrackSearchParams } from "../../../objects/classes/searchParams/LaughtrackSearchParams";

interface HomeSearchFormProps {
    citiesString: string;
}

export default function HomeSearchForm({ citiesString }: HomeSearchFormProps) {
    const params = LaughtrackSearchParams.asClientSideParams(
        new URLSearchParams(useSearchParams()),
        usePathname(),
        useRouter(),
    );
    const cities = JSON.parse(citiesString) as FormSelectable[];

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

    function onSubmit(values: z.infer<typeof homeSearchSchema>) {
        params.setParamValue(URLParam.City, values.cityId);
        params.setParamValue(URLParam.StartDate, values.dates.from);
        params.setParamValue(URLParam.EndDate, values.dates.to);
        params.pushPageFromParams(`search`);
    }

    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="flex flex-col lg:flex-row lg:max-w-6xl
                lg:mx-auto items-start justify-center space-x-0 lg:space-x-2
                space-y-4 lg:space-y-0 rounded-lg"
            >
                <DropdownFormComponent
                    name="cityId"
                    title="City"
                    placeholder="Select your city"
                    items={cities}
                    form={form}
                />
                <CalendarFormComponent name="dates" form={form} />
                <div className="grid lg:max-w-sm flex-0 gap-1.5">
                    <div className="h-3"></div>
                    <div className="mt-auto">
                        <Button
                            type="submit"
                            className="bg-silver-gray rounded-lg"
                        >
                            Search
                        </Button>
                    </div>
                </div>
            </form>
        </Form>
    );
}
