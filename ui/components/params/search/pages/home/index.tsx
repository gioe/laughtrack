"use client";

import { z } from "zod";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { CircleIconButton } from "@/ui/components/button/circleIcon";
import { Search } from "lucide-react";
import { showSearchFormSchema } from "./schema";
import { Loader2 } from "lucide-react";
import { Form } from "@/ui/components/ui/form";
import { ComponentVariant, StyleContextKey } from "@/objects/enum";
import CalendarComponent from "../../components/calendar";
import ShowLocationComponent from "../../components/area";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarContainer from "../../components/container";

const LoadingOverlay = () => (
    <div className="absolute inset-0 bg-black/20 backdrop-blur-sm rounded-full flex items-center justify-center z-10">
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
                className="relative w-full"
            >
                <SearchBarContainer variant={StyleContextKey.Home}>
                    {isLoading && <LoadingOverlay />}

                    <div className="flex-1 flex items-center pr-4 border-r">
                        <ShowLocationComponent
                            variant={ComponentVariant.Form}
                            form={form}
                        />
                    </div>

                    <div className="flex-1 px-4">
                        <CalendarComponent
                            variant={ComponentVariant.Form}
                            name="dates"
                            form={form}
                        />
                    </div>

                    <div className="ml-auto">
                        <CircleIconButton
                            type="submit"
                            isLoading={isLoading}
                            className="bg-copper"
                        >
                            <Search className="text-white" />
                        </CircleIconButton>
                    </div>
                </SearchBarContainer>
            </form>
        </Form>
    );
}
