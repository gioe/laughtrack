"use client";

import { CalendarVariant } from "@/ui/components/calendar";
import { z } from "zod";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { CircleIconButton } from "@/ui/components/button/circleIcon";
import { Calendar, ChevronsUpDown, MapPin, Search } from "lucide-react";
import { showSearchFormSchema } from "./schema";
import { QueryProperty } from "@/objects/enum";
import { Loader2 } from "lucide-react";
import CalendarComponent from "@/ui/components/calendar";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "@/objects/class/params/SearchParamsHelper";
import { Navigator } from "@/objects/class/navigate/Navigator";
import { Form } from "@/ui/components/ui/form";
import ShowDistanceSelectionComponent, {
    DistanceComponentVariant,
} from "@/ui/components/area";

const LoadingOverlay = () => (
    <div className="absolute inset-0 bg-black/20 backdrop-blur-sm rounded-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-white animate-spin" />
    </div>
);

export default function ShowSearchForm() {
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

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
            // Add validation debugging
            const validationResult = showSearchFormSchema.safeParse(data);
            if (!validationResult.success) {
                console.log(
                    "Validation errors:",
                    validationResult.error.errors,
                );
                return;
            }

            setIsLoading(true);
            const map = new Map<URLParam, ParamsDictValue>();
            map.set(QueryProperty.Distance, data.distance.distance);
            map.set(QueryProperty.Zip, data.distance.zipCode);
            map.set(QueryProperty.FromDate, data.dates.from);
            map.set(QueryProperty.ToDate, data.dates.to);

            await new Promise((resolve) => setTimeout(resolve, 300));

            paramsHelper.updateParamsFromMap(map);
            navigator.pushPage("show/all", paramsHelper.asParamsString());
        } catch (error) {
            console.error("Error during navigation:", error);
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(submitForm)} className="relative">
                <div className="flex flex-col md:flex-row items-stretch md:items-center bg-ivory/20 backdrop-blur rounded-2xl md:rounded-full overflow-hidden">
                    {isLoading && <LoadingOverlay />}

                    <div className="flex-1 border-b md:border-b-0 md:border-r border-gray-600/30">
                        <div className="px-4 md:px-8 py-4">
                            <ShowDistanceSelectionComponent
                                variant={DistanceComponentVariant.Form}
                                name="distance"
                                form={form}
                                icon={
                                    <MapPin className="w-5 h-5 text-white/80" />
                                }
                            />
                        </div>
                    </div>

                    <div className="flex">
                        <div className="px-4 md:px-8 py-4">
                            <CalendarComponent
                                variant={CalendarVariant.Form}
                                name="dates"
                                form={form}
                                placeholder="When"
                                icon={
                                    <Calendar className="w-5 h-5 text-white/80" />
                                }
                            />
                        </div>
                    </div>

                    <div className="px-4 md:px-6 py-4 md:py-0 flex justify-center md:justify-start">
                        <CircleIconButton
                            type="submit"
                            isLoading={isLoading}
                            className="bg-copper w-full md:w-auto"
                        >
                            <Search className="w-5 h-5 text-white" />
                        </CircleIconButton>
                    </div>
                </div>
            </form>
        </Form>
    );
}
