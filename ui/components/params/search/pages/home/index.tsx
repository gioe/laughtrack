"use client";

import { z } from "zod";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Search } from "lucide-react";
import { showSearchFormSchema } from "./schema";
import { Loader2 } from "lucide-react";
import { Form } from "@/ui/components/ui/form";
import { ComponentVariant, StyleContextKey } from "@/objects/enum";
import CalendarComponent from "../../components/calendar";
import ShowLocationComponent from "../../components/area";
import { useUrlParams } from "@/hooks/useUrlParams";

const LoadingOverlay = () => (
    <div className="absolute inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-10">
        <Loader2 className="w-6 h-6 text-white animate-spin" />
    </div>
);

export default function ShowSearchForm() {
    const { setMultipleTypedParams } = useUrlParams();
    const [isLoading, setIsLoading] = useState(false);

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

            setIsLoading(true);
            await new Promise((resolve) => setTimeout(resolve, 300));

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
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(submitForm)}
                className="w-full max-w-3xl mx-auto"
            >
                <div className="relative bg-zinc-900/80 backdrop-blur-md shadow-xl rounded-2xl overflow-hidden border border-white/10">
                    {isLoading && <LoadingOverlay />}

                    <div className="flex flex-col lg:flex-row">
                        <div className="flex-1 p-4 lg:p-6">
                            <div className="flex flex-col lg:flex-row items-center lg:divide-x divide-white/10">
                                <div className="w-full lg:w-auto mb-4 lg:mb-0 lg:pr-10">
                                    <ShowLocationComponent
                                        variant={ComponentVariant.Form}
                                        form={form}
                                    />
                                </div>
                                <div className="w-full lg:w-auto lg:pl-10">
                                    <CalendarComponent
                                        variant={ComponentVariant.Form}
                                        name="dates"
                                        form={form}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="lg:border-l border-white/10">
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full lg:w-auto h-full px-8 py-4 lg:px-10 bg-copper hover:bg-copper/90
                                         transition-colors flex items-center justify-center gap-3 text-white
                                         font-medium"
                            >
                                <Search className="w-6 h-6" />
                                <span className="lg:hidden">Search Shows</span>
                            </button>
                        </div>
                    </div>
                </div>
            </form>
        </Form>
    );
}
