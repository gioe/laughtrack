import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Calendar } from "../ui/calendar";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { Calendar as CalIcon, ChevronsUpDown } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { UseFormReturn } from "react-hook-form";
import { cn } from "@/util/tailwindUtil";
import { formatDateRange } from "@/util/primatives/dateUtil";

export interface DateRange {
    from: Date;
    to?: Date;
}

// Base props that both variants share
interface BaseCalendarProps {
    name: string;
}

// Props for the form variant
interface FormCalendarProps extends BaseCalendarProps {
    form: UseFormReturn<any>;
    onValueChange?: never; // Ensure onValueChange is not provided with form
    value?: never;
}

// Props for the standalone variant
interface StandaloneCalendarProps extends BaseCalendarProps {
    form?: never; // Ensure form is not provided with onValueChange
    onValueChange: (value: DateRange | undefined) => void;
    value?: DateRange;
}

// Combined type using discriminated union
type CalendarComponentProps = FormCalendarProps | StandaloneCalendarProps;

const CalendarComponent = (props: CalendarComponentProps) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const controlClasses = `text-xl rounded-lg px-3 lg:w-80 lg:h-12 ${styleConfig.iconTextColor} ring-transparent focus:ring-transparent border-transparent focus:outline-none outline-none`;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Common calendar content
    const CalendarContent = ({
        selected,
        onSelect,
    }: {
        selected?: DateRange;
        onSelect: (value: DateRange | undefined) => void;
    }) => (
        <div className="flex items-center gap-2">
            <CalIcon className={cn("w-5 h-5", styleConfig.iconTextColor)} />
            <Popover>
                <PopoverTrigger asChild>
                    <div className={controlClasses}>
                        <div className="flex items-center justify-between w-full">
                            <span
                                className={cn(
                                    "text-[16px]",
                                    styleConfig.iconTextColor,
                                )}
                            >
                                {formatDateRange(selected)}
                            </span>
                            <ChevronsUpDown
                                className={cn(
                                    "w-3 h-3",
                                    styleConfig.iconTextColor,
                                )}
                                style={{ opacity: 0.5 }}
                            />
                        </div>
                    </div>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 rounded-lg" align="start">
                    <Calendar
                        className="rounded-lg"
                        initialFocus
                        mode="range"
                        selected={selected}
                        defaultMonth={selected?.from}
                        onSelect={onSelect}
                        numberOfMonths={2}
                        disabled={(date) => date < today}
                    />
                </PopoverContent>
            </Popover>
        </div>
    );

    // Render for form-controlled calendar
    if (props.form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem className="flex flex-col">
                        <FormControl className={controlClasses}>
                            <CalendarContent
                                selected={field.value}
                                onSelect={field.onChange}
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    }

    // Render for standalone calendar
    return (
        <CalendarContent
            selected={props.value}
            onSelect={props.onValueChange}
        />
    );
};

export default CalendarComponent;
