"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from 'next/navigation';
import { useForm } from "react-hook-form";
import * as z from "zod";
import { Button } from "@/components/ui/button"
import { CalendarIcon, LaughIcon } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { format } from 'date-fns';

import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage
} from "@/components/ui/form"
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Calendar } from "./ui/calendar";

export const formSchema = z.object({
    comics: z.string().min(2).max(50),
    dates: z.object({
        from: z.date(),
        to: z.date()
    })
})

function SearchForm() {
    const router = useRouter();

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            comics: "",
            dates: {
                from: undefined,
                to: undefined
            }
        }
    })

    function onSubmit(values: z.infer<typeof formSchema>) {
        const startDayDate = values.dates.from.getDate().toString();
        const startDayMonth = (values.dates.from.getMonth() + 1).toString();
        const startDayYear = values.dates.from.getFullYear().toString();
        const endDateDate = values.dates.to.getDate().toString();
        const endDateMonth = (values.dates.to.getDate() + 1).toString();
        const endDateYear = values.dates.to.getDate().toString();

        router.push(`search?comics=${values.comics}&from=${values.dates.from}&to=${values.dates.to}`)

    }

    return <Form {...form}>
        <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col lg:flex-row lg:max-w-6xl lg:mx-auto items-center justify-center
        space-x-0 lg:space-x-2 space-y-4 lg:space-y-0 rounded-lg" >
            <div className="grid w-full lg:max-w-sm items-center gap-1.5">
                <FormField
                    control={form.control}
                    name="comics"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel className="text-white flex">
                                <LaughIcon className="ml-2 h-4 w-4 text-white" />
                            </FormLabel>
                            <FormMessage />
                            <FormControl>
                                <Input placeholder="Dave Chappelle" {...field} />
                            </FormControl>
                        </FormItem>
                    )}
                />
            </div>
            <div className="grid w-full lg:max-w-sm flex-1 items-center gap-1.5">
                <FormField
                    control={form.control}
                    name="dates"
                    render={({ field }) => (
                        <FormItem className="flex flex-col">
                            <FormLabel className="text-white">Dates</FormLabel>
                            <FormMessage />
                            <Popover >
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            id="date"
                                            name="dates"
                                            variant={"outline"}
                                            className={cn(
                                                "w-full lg:w-[300px] justify-start text-left font-normal",
                                                !field.value.from && "text-muted-foreground"
                                            )}
                                        >
                                            <CalendarIcon className="mr-3 h-4 w-4 opacity-50%" />
                                            {field.value?.from ? (
                                                field.value?.to ? (
                                                    <>
                                                        {format(field.value?.from, "LLL dd, y")} -{" "}
                                                        {format(field.value?.to, "LLL dd, y")}
                                                    </>
                                                ) : (
                                                    format(field.value?.from, "LLL dd, y")
                                                )
                                            ) : (
                                                <span> Select your dates </span>
                                            )}
                                        </Button>
                                    </FormControl>
                                </PopoverTrigger>
                                <PopoverContent className="w-auto p-0" align="start">
                                    <Calendar
                                        initialFocus
                                        mode="range"
                                        selected={field.value}
                                        defaultMonth={field.value.from}
                                        onSelect={field.onChange}
                                        numberOfMonths={2}
                                        disabled={(date) => {
                                            return date < new Date(new Date().setHours(0, 0, 0, 0))
                                        }}
                                    >
                                    </Calendar>
                                </PopoverContent>
                            </Popover>
                        </FormItem>
                    )}
                />
            </div>
            <div className="flex w-full items-center space-x-2">
            <div className="mt-auto">
                <Button type="submit" className="bg-blue-500 text-base">
                        Search
                        </Button>
            </div>
            </div>
        </form>
    </Form>
}

export default SearchForm