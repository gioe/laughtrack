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
            const validationResult = showSearchFormSchema.safeParse(data);
            if (!validationResult.success) {
                console.log(
                    "Validation errors:",
                    validationResult.error.errors,
                );
                return;
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
                <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-2xl overflow-hidden">
                    <div className="flex flex-col sm:flex-row sm:items-stretch">
                        {/* Location section */}
                        <div className="flex-1 px-6 pt-5 pb-4 sm:py-5">
                            <label
                                htmlFor="show-search-zip"
                                className="text-xs font-semibold text-white/50 uppercase tracking-widest mb-2.5 block"
                            >
                                Where
                            </label>
                            <ShowLocationComponent
                                variant={ComponentVariant.Form}
                                form={form}
                                inputId="show-search-zip"
                            />
                        </div>

                        {/* Vertical divider (desktop) / Horizontal divider (mobile) */}
                        <div className="hidden sm:block w-px bg-white/15 my-4" />
                        <div className="sm:hidden h-px bg-white/15 mx-6" />

                        {/* Dates section */}
                        <div className="flex-1 px-6 pt-4 sm:pt-5 pb-5">
                            <p
                                id="show-search-dates-label"
                                className="text-xs font-semibold text-white/50 uppercase tracking-widest mb-2.5"
                            >
                                When
                            </p>
                            <CalendarComponent
                                variant={ComponentVariant.Form}
                                name="dates"
                                form={form}
                                inputId="show-search-dates-label"
                            />
                        </div>

                        {/* Search button */}
                        <div className="px-5 pb-5 sm:py-4 sm:pr-4 sm:flex sm:items-center sm:pl-3">
                            <button
                                type="submit"
                                aria-label="Find Shows"
                                className="w-full sm:w-auto px-7 py-3 bg-copper hover:bg-copper/90
                                           active:scale-[0.98] transition-all duration-150
                                           rounded-xl flex items-center justify-center gap-2.5
                                           text-white font-semibold text-base
                                           shadow-lg shadow-black/20"
                            >
                                <Search className="w-5 h-5" />
                                Find Shows
                            </button>
                        </div>
                    </div>
                </div>
            </form>
        </Form>
    );
}
