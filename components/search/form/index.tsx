"use client";

import { useForm } from "react-hook-form";
import { Button } from "../../ui/button";
import { Form } from "../../ui/form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
    formattedDateParam,
    updateMultipleParams,
} from "../../../util/primatives/paramUtil";
import { URLParam } from "../../../util/enum";
import { pushNewPage } from "../../../util/navigationUtil";
import { useRouter } from "next/navigation";
import { DropdownFormComponent } from "../../formComponents/dropdown";
import CalendarFormComponent from "../../formComponents/calendar";
import { homeSearchSchema } from "./schema";

interface HomeSearchFormProps {
    cities: string[];
}

export default function HomeSearchForm({ cities }: HomeSearchFormProps) {
    const router = useRouter();

    const form = useForm<z.infer<typeof homeSearchSchema>>({
        resolver: zodResolver(homeSearchSchema),
        defaultValues: {
            location: "",
            dates: {
                from: undefined,
                to: undefined,
            },
        },
    });

    function onSubmit(values: z.infer<typeof homeSearchSchema>) {
        const params = new URLSearchParams();
        updateMultipleParams(params, [
            {
                value: values.location,
                key: URLParam.Location,
            },
            {
                value: formattedDateParam(values.dates.from),
                key: URLParam.StartDate,
            },
            {
                value: formattedDateParam(values.dates.to),
                key: URLParam.EndDate,
            },
        ]);
        pushNewPage(params, router, "search");
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
                    name="location"
                    title="Location"
                    placeholder="Select your location"
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
