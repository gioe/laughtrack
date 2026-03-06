import { Input } from "@/ui/components/ui/input";
import { ChangeEvent, useCallback, useEffect, useRef, useState } from "react";

interface TextInputComponentProps {
    icon: React.ReactNode;
    placeholder: string;
    value?: string;
    onChange?: (value: string) => void;
    debounceTime?: number;
    className?: string;
}

const TextInputComponent = ({
    icon,
    placeholder,
    value = "",
    onChange,
    debounceTime = 500,
    className,
    ...props
}: TextInputComponentProps) => {
    const [inputValue, setInputValue] = useState(value);
    const timerRef = useRef<ReturnType<typeof setTimeout>>();

    useEffect(() => () => clearTimeout(timerRef.current), []);

    // Get the debounced value
    const debouncedOnChange = useCallback(
        (value: string) => {
            clearTimeout(timerRef.current);
            timerRef.current = setTimeout(() => {
                onChange?.(value);
            }, debounceTime);
        },
        [onChange, debounceTime],
    );

    // Update local value when prop value changes
    useEffect(() => {
        setInputValue(value);
    }, [value]);

    // Handle input changes
    const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
        const newValue = event.target.value;
        setInputValue(newValue);
        debouncedOnChange(newValue);
    };

    return (
        <div className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg bg-transparent transition-colors hover:border-gray-400 focus-within:border-gray-400 focus-within:ring-2 focus-within:ring-blue-500 focus-within:outline-none">
            {icon}
            <Input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                placeholder={placeholder}
                className={`border-0 px-0 focus:ring-0 focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0 ${className}`}
                {...props}
            />
        </div>
    );
};

export default TextInputComponent;
