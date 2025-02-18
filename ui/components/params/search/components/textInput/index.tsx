interface TextInputComponentProps {
    icon: React.ReactNode;
    placeholder: string;
    value?: string;
    onChange?: (value: string) => void;
    className?: string;
}

const TextInputComponent = ({
    icon,
    placeholder,
    value,
    onChange,
    className = "",
}: TextInputComponentProps) => {
    return (
        <div className={`flex items-center flex-1 ${className}`}>
            {icon}
            <input
                type="text"
                placeholder={placeholder}
                value={value}
                onChange={(e) => onChange?.(e.target.value)}
                className="outline-none w-full bg-ivory border-none
                font-dmSans text-cedar text-[16px]
                focus:outline-none focus:border-none
                placeholder:font-dmSans placeholder:text-[16px]"
            />
        </div>
    );
};

export default TextInputComponent;
