/* eslint-disable @typescript-eslint/no-explicit-any */

import { CheckboxFormComponent } from "../../../../../../../../components/checkbox";
import { FormFileInput } from "../../../../../../../../components/input/file";
import { FormTextInput } from "../../../../../../../../components/input/text";
import SocialDataFormInput from "../../../../../../../../components/social/input";
import { useDataProvider } from "../../../../../../../../contexts/EntityPageDataProvider";
import { Comedian } from "../../../../../../../../objects/class/comedian/Comedian";
import { Filter } from "../../../../../../../../objects/class/filter/Filter";
import { Tag } from "../../../../../../../../objects/class/filter/FilterOption";
import { EntityType } from "../../../../../../../../objects/enum";
import { allSocialMedia } from "../../../../../../../../objects/enum/socialMedia";
import { Selectable } from "../../../../../../../../objects/interface";

interface EditComedianFormBodyProps {
    comedian: Comedian;
    isLoading: boolean;
    form: any;
}

export default function EditComedianFormBody({
    comedian,
    isLoading,
    form,
}: EditComedianFormBodyProps) {
    const { filters } = useDataProvider();

    const selectables = filters
        .filter((filter: Filter) => filter.type === EntityType.Comedian)
        .flatMap((filter: Filter) => filter.options)
        .map((tag: Tag) => {
            return {
                id: tag.id,
                displayName: tag.displayName,
                value: tag.value,
                selected: comedian.tagIds.includes(tag.id),
            };
        }) as Selectable[];

    return (
        <div className="flex flex-col gap-2 mx-4">
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
            <FormTextInput
                key={"website"}
                isLoading={isLoading}
                name={"website"}
                placeholder={"Website"}
                form={form}
            />
            <FormTextInput
                key={"linktree"}
                isLoading={isLoading}
                name={"linktree"}
                placeholder={"Linktree"}
                form={form}
            />
            <FormFileInput
                key={"bannerImage"}
                isLoading={isLoading}
                name={"bannerImage"}
                placeholder={"Banner Image"}
                form={form}
            />
            <FormFileInput
                key={"cardImage"}
                isLoading={isLoading}
                name={"cardImage"}
                placeholder={"Card Image"}
                form={form}
            />
            <div className="mt-5">
                <CheckboxFormComponent form={form} selectables={selectables} />
            </div>
        </div>
    );
}
