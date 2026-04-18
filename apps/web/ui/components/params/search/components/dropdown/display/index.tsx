import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../../../../../ui/select";
import { Selectable } from "@/objects/interface";
import { useStyleContext } from "@/contexts/StyleProvider";

// Props for the standalone variant
interface DropdownDisplayProps {
    placeholder?: string;
    onChange: (value: any) => void;
    value?: any;
    items: Selectable[];
    // Static id for SelectContent and SelectTrigger aria-controls — bypasses
    // Radix's internal useId which can drift across SSR/hydration. Callers
    // must ensure uniqueness when multiple instances render on the same page.
    contentId?: string;
}

export function DropdownDisplay(props: DropdownDisplayProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    return (
        <div className="flex items-center">
            <Select onValueChange={props.onChange} value={props.value}>
                <SelectTrigger
                    className={`text-[18px] ${styleConfig.inputTextColor} font-dmSans h-9 border-gray-300 shadow-none hover:border-gray-400 focus:border-gray-400`}
                    {...(props.contentId
                        ? { "aria-controls": props.contentId }
                        : {})}
                >
                    <SelectValue
                        className="text-left pr-2"
                        placeholder={props.placeholder}
                    />
                </SelectTrigger>
                <SelectContent
                    className="rounded-lg bg-white border border-gray-300"
                    {...(props.contentId ? { id: props.contentId } : {})}
                >
                    {props.items.map((item) => (
                        <SelectItem
                            className="rounded-lg text-gray-900 hover:text-gray-700 focus:text-gray-700"
                            key={item.id.toString()}
                            value={item.slug}
                        >
                            {item.name}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}

export default DropdownDisplay;
