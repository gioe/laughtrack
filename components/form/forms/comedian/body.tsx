/* eslint-disable @typescript-eslint/no-explicit-any */

import SocialDataFormInput from "../../components/social";
import { allSocialMedia } from "../../../../objects/enum/socialMedia";
import { useDataProvider } from "../../../../contexts/EntityPageDataProvider";
import { Filter } from "../../../../objects/class/tag/Filter";
import { CheckboxFormComponent } from "../../components/checkbox";
import { Tag } from "../../../../objects/class/tag/Tag";
import { FormTextInput } from "../../components/input/text";
import { FormFileInput } from "../../components/input/file";
import { Comedian } from "../../../../objects/class/comedian/Comedian";
import { EntityType } from "../../../../objects/enum";
import { Selectable } from "../../../../objects/interface";
import WebView from "../../../webview";

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
        <div className="flex flex-row gap-2 mt-10">
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
                    <CheckboxFormComponent
                        form={form}
                        selectables={selectables}
                    />
                </div>
            </div>
            <div className="flex flex-col gap-2 mx-4">
                {comedian.socialData?.website && (
                    <WebView url={comedian.socialData.website} />
                )}
            </div>
        </div>
    );
}
