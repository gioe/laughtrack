import React from "react";
import { Input, InputProps } from "../../ui/input";

const ZipCodeInput = (
    props: React.JSX.IntrinsicAttributes &
        InputProps &
        React.RefAttributes<HTMLInputElement>,
) => {
    return (
        <div className="space-y-2">
            <Input type="text" maxLength={5} pattern="[0-9]{5}" {...props} />
        </div>
    );
};

export default ZipCodeInput;
