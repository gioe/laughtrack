"use client";

import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Search } from "lucide-react";
import { showSearchFormSchema } from "./schema";
import { Form } from "@/ui/components/ui/form";
import { ComponentVariant } from "@/objects/enum";
import CalendarComponent from "../../components/calendar";
import ShowLocationComponent from "../../components/area";
import { useUrlParams } from "@/hooks/useUrlParams";
import { resolveLocationAction } from "@/app/actions/resolveLocationAction";
import SearchBarLayout, { SearchChipRow } from "../../components/layout";

export default function ShowSearchForm() {
    const { setMultipleTypedParams } = useUrlParams();

    const form = useForm<z.infer<typeof showSearchFormSchema>>({
        resolver: zodResolver(showSearchFormSchema),
        defaultValues: {
            distance: {
                distance: "5",
                zipCode: "",
            },
            dates: {
                from: undefined,
                to: undefined,
            },
        },
    });

    async function submitForm(data: z.infer<typeof showSearchFormSchema>) {
        try {
            // If the input looks like a city name (not a 5-digit zip), verify it
            // exists in the zipcodes dataset before navigating.
            if (!/^\d{5}$/.test(data.distance.zipCode)) {
                const locationResult = await resolveLocationAction(
                    data.distance.zipCode,
                );
                if (!locationResult.ok) {
                    form.setError("distance.zipCode", {
                        message: locationResult.error,
                    });
                    return;
                }
            }

            setMultipleTypedParams(
                {
                    distance: data.distance.distance,
                    zip: data.distance.zipCode,
                    fromDate: data.dates.from,
                    toDate: data.dates.to,
                },
                "show/search",
            );
        } catch (error) {
            console.error("Error during navigation:", error);
        }
    }

    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(submitForm)}
                className="w-full max-w-3xl mx-auto"
            >
                <SearchBarLayout maxWidth="max-w-3xl">
                    <SearchChipRow ariaLabel="Home show search filters">
                        <ShowLocationComponent
                            variant={ComponentVariant.Form}
                            form={form}
                            inputId="show-search-zip"
                            dropdownId="home-show-search-distance"
                        />
                        <CalendarComponent
                            variant={ComponentVariant.Form}
                            name="dates"
                            form={form}
                        />
                        <button
                            type="submit"
                            aria-label="Find Shows"
                            className="flex h-10 w-full items-center justify-center gap-2.5 rounded-full bg-copper px-7 text-base font-semibold text-white shadow-lg shadow-black/20 transition-all duration-150 hover:bg-copper/90 active:scale-[0.98] sm:w-auto"
                        >
                            <Search className="w-5 h-5" />
                            Find Shows
                        </button>
                    </SearchChipRow>
                </SearchBarLayout>
            </form>
        </Form>
    );
}
