"use client";

import { useForm } from "react-hook-form";
import { Button } from "../../ui/button";
import { Form } from "../../ui/form";
import { zodResolver } from "@hookform/resolvers/zod";
import { searchSchema } from "../../../schemas";
import { z } from "zod";
import {
    formattedDateParam,
    updateMultipleParams,
} from "../../../util/primatives/paramUtil";
import { URLParam } from "../../../util/enum";
import { pushNewPage } from "../../../util/navigationUtil";
import CalendarComponent from "../calendar/CalendarComponent";
import { Dropdown } from "../dropdown/Dropdown";
import { useRouter } from "next/navigation";

interface SearchFormProps {
    cities: string[];
}

export default function SearchForm({ cities }: SearchFormProps) {
    const router = useRouter();

    function onSubmit(values: z.infer<typeof searchSchema>) {
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

    const form = useForm<z.infer<typeof searchSchema>>({
        resolver: zodResolver(searchSchema),
        defaultValues: {
            location: "",
            dates: {
                from: undefined,
                to: undefined,
            },
        },
    });

    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="flex flex-col lg:flex-row lg:max-w-6xl
                lg:mx-auto items-start justify-center space-x-0 lg:space-x-2
                space-y-4 lg:space-y-0 rounded-lg"
            >
                <Dropdown
                    name="location"
                    title="Location"
                    placeholder="Select your location"
                    items={cities}
                    form={form}
                />
                <CalendarComponent name="dates" form={form} />
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
