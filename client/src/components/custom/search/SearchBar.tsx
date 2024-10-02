'use client';
import { useRouter } from 'next/navigation';
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { Button } from '@/components/ui/button'
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage
} from '@/components/ui/form'
import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem
} from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { Calendar } from '@/components/ui/calendar'
import { cn } from "@/lib/utils"

interface SearchBarProps {
    cities: string[];
}

export const formSchema = z.object({
    location: z
        .string({
            required_error: "Please select a location.",
        }),
    dates: z.object({
        from: z.date(),
        to: z.date()
    })
})

const SearchBar: React.FC<SearchBarProps> = ({
    cities
}) => {

    const router = useRouter();

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            location: "",
            dates: {
                from: undefined,
                to: undefined
            }
        }
    })

    function onSubmit(values: z.infer<typeof formSchema>) {
        const params = new URLSearchParams();

        const earliest_monthday = values.dates.from.getDate().toString();
        const earliest_month = (values.dates.from.getMonth() + 1).toString();
        const earliest_year = values.dates.from.getFullYear().toString()

        const latest_monthday = values.dates.to.getDate().toString();
        const latest_month = (values.dates.to.getMonth() + 1).toString();
        const latest_year = values.dates.to.getFullYear().toString()

        params.set("location", values.location);
        params.set("startDate", `${earliest_year}-${earliest_month}-${earliest_monthday}`);
        params.set("endDate",  `${latest_year}-${latest_month}-${latest_monthday}`);

        router.push(`/search?${params.toString()}`);
    }


    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className='flex flex-col lg:flex-row lg:max-w-6xl lg:mx-auto items-center justify-center
         space-x-0 lg:space-x-2 space-y-4 lg:space-y-0 rounded-lg'
            >
                <div className='grid w-full lg:max-w-sm flex-1 items-center gap-1.5'>
                <FormField
                        control={form.control}
                        name="location"
                        render={({ field }) => (
                            <FormItem className='flex flex-col'>
                                <FormLabel className='text-white'>Location</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl className='bg-white'>
                                        <SelectTrigger>
                                            <SelectValue className='bg-white' placeholder="Select a location" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent className='bg-white'>
                                        {
                                            cities.map((city: string ) => (
                                                <SelectItem className='bg-white' value={city}>{city}</SelectItem>
                                            ))
                                        }
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <div className='grid w-full lg:max-w-sm flex-1 items-center gap-1.5'>
                    <FormField
                        control={form.control}
                        name="dates"
                        render={({ field }) => (
                            <FormItem className='flex flex-col'>
                                <FormLabel className='text-white'>Dates</FormLabel>
                                <FormMessage />
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                id="date"
                                                name="dates"
                                                variant={'outline'}
                                                className={cn(
                                                    "w-full lg:w-[300px] justify-start text-left font-normal",
                                                    !field.value.from && "text-muted-foreground"
                                                )}
                                            >
                                                <CalendarIcon className="mr-3 h-4 w-4 opacity-50" />
                                                {field.value?.from ? (
                                                    field.value?.to ? (
                                                        <>
                                                            {format(field.value?.from, "LLL dd, yyyy")} -{" "}
                                                            {format(field.value?.to, "LLL dd, yyyy")}
                                                        </>
                                                    ) : (
                                                        format(field.value?.from, "LLL dd, yyyy")
                                                    )
                                                ) : (
                                                    <span>Select your dates</span>
                                                )}
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className='w-auto p-0' align='start'>
                                        <Calendar
                                            initialFocus
                                            mode="range"
                                            selected={field.value}
                                            defaultMonth={field.value.from}
                                            onSelect={field.onChange}
                                            numberOfMonths={2}
                                            disabled={(date) =>
                                                date < new Date(new Date().setHours(0, 0, 0, 0))
                                            }
                                        >

                                        </Calendar>
                                    </PopoverContent>
                                </Popover>
                            </FormItem>
                        )}
                    >
                    </FormField>
                </div>


                <div className='grid lg:max-w-sm flex-1 gap-1.5'>
                <div className='h-3'></div>
                <div className='mt-auto'>
                        <Button type='submit' className='bg-silver-gray'>
                            Search
                        </Button>
                    </div>
                </div>

            </form>
        </Form>
    )
}

export default SearchBar;