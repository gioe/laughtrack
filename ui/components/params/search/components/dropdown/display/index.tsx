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
}

export function DropdownDisplay(props: DropdownDisplayProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    return (
        <div className="flex items-center">
            <Select onValueChange={props.onChange} value={props.value}>
                <SelectTrigger
                    className={`text-[18px] ${styleConfig.inputTextColor} font-dmSans h-9 border-transparent shadow-none`}
                >
                    <SelectValue
                        className="text-left pr-2"
                        placeholder={props.placeholder}
                    />
                </SelectTrigger>
                <SelectContent className="rounded-lg bg-white">
                    {props.items.map((item) => (
                        <SelectItem
                            className="rounded-lg"
                            key={item.id.toString()}
                            value={item.value}
                        >
                            {item.display}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}

export default DropdownDisplay;
