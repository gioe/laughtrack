"use client";

import { SocialMedia } from "../../../objects/enum";
import { FormNumberInput } from "../../input/number";
import { FormTextInput } from "../../input/text";

interface SocialDataFormInputProps {
    isLoading: boolean;
    socialMedia: SocialMedia;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

const SocialDataFormInput: React.FC<SocialDataFormInputProps> = ({
    isLoading,
    form,
    socialMedia,
}) => {
    return (
        <div className="gap-2 w-full relative flex flex-col">
            <div className="w-full relative flex flew-row gap-2">
                <FormTextInput
                    isLoading={isLoading}
                    name={`${socialMedia.valueOf().toLowerCase()}.account`}
                    placeholder={`${socialMedia.valueOf()} Account`}
                    form={form}
                />
                <FormNumberInput
                    isLoading={isLoading}
                    name={`${socialMedia.valueOf().toLowerCase()}.following`}
                    placeholder={`${socialMedia.valueOf()} Followers`}
                    form={form}
                />
            </div>
        </div>
    );
};

export default SocialDataFormInput;
