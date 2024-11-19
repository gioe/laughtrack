/* eslint-disable @typescript-eslint/no-explicit-any */

import SocialDataFormInput from "../../components/social";
import { allSocialMedia } from "../../../../objects/enum/socialMedia";
import { FormInput } from "../../components/input";

interface EditSocialDataFormBodyProps {
    isLoading: boolean;
    form: any;
}

export default function EditSocialDataFormBody({
    isLoading,
    form,
}: EditSocialDataFormBodyProps) {
    const additionalInputs = [
        {
            type: "text",
            name: "website",
            placeholder: "Webite",
        },
        {
            type: "file",
            name: "bannerImage",
            placeholder: "Banner Image",
        },
        {
            type: "file",
            name: "cardImage",
            placeholder: "Card Image",
        },
    ];

    return (
        <div className="flex flex-col gap-2">
            {allSocialMedia.map((value) => {
                return (
                    <SocialDataFormInput
                        isLoading={isLoading}
                        key={value.valueOf()}
                        form={form}
                        socialMedia={value}
                    />
                );
            })}
            {additionalInputs.map((metadata) => {
                return (
                    <FormInput
                        isLoading={isLoading}
                        type={metadata.type}
                        name={metadata.name}
                        placeholder={metadata.placeholder}
                        form={form}
                    />
                );
            })}
        </div>
    );
}
