"use client";

import { SocialMedia } from "../../../../util/enum";
import { Input } from "../../../ui/input";
import {
    FormControl,
    FormField,
    FormItem,
    FormMessage,
} from "../../../ui/form";

interface SocialDataFormInputProps {
    socialMedia: SocialMedia;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

const SocialDataFormInput: React.FC<SocialDataFormInputProps> = ({
    form,
    socialMedia,
}) => {
    return (
        <div className="pt-3 gap-2 w-full relative flex flex-col">
            {socialMedia.valueOf()}
            <div className="w-full relative flex flew-row gap-2">
                <FormField
                    control={form.control}
                    name={`${socialMedia.valueOf().toLowerCase()}.account`}
                    render={({ field }) => {
                        return (
                            <FormItem>
                                <FormControl>
                                    <Input
                                        type="text"
                                        placeholder={`${socialMedia.valueOf()} Account`}
                                        {...field}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        );
                    }}
                />
                <FormField
                    control={form.control}
                    name={`${socialMedia.valueOf().toLowerCase()}Followers`}
                    render={({ field }) => {
                        return (
                            <FormItem>
                                <FormControl>
                                    <Input
                                        type="number"
                                        placeholder={`${socialMedia.valueOf()} Followers`}
                                        {...field}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        );
                    }}
                />
            </div>
        </div>
    );
};

export default SocialDataFormInput;
