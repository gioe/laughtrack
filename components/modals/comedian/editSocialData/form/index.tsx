"use client";

import { SocialMedia } from "../../../../../util/enum";
import { FormInput } from "../../../../formComponents/input";
import SocialDataFormInput from "../../../../formComponents/social";

interface EditSocialDataInterfaceProps {
    isLoading: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

const ALL_SOCIAL_MEDIA = [
    SocialMedia.Facebook,
    SocialMedia.Instagram,
    SocialMedia.TikTok,
    SocialMedia.Twitter,
    SocialMedia.YouTube,
];

export default function EditSocialDataForm({
    isLoading,
    form,
}: EditSocialDataInterfaceProps) {
    return (
        <div className="flex flex-col gap-2">
            {ALL_SOCIAL_MEDIA.map((value) => {
                return (
                    <SocialDataFormInput
                        isLoading={isLoading}
                        key={value.valueOf()}
                        form={form}
                        socialMedia={value}
                    />
                );
            })}
            <FormInput
                isLoading={isLoading}
                type={"text"}
                name={`website`}
                placeholder={`Website`}
                form={form}
            />
            <FormInput
                isLoading={isLoading}
                type={"file"}
                name={`bannerImage`}
                placeholder={""}
                form={form}
            />
            <FormInput
                isLoading={isLoading}
                type={"file"}
                name={`cardImage`}
                placeholder={""}
                form={form}
            />
        </div>
    );
}
