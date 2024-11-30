/* eslint-disable @typescript-eslint/no-explicit-any */

import SocialDataFormInput from "../../components/social";
import { allSocialMedia } from "../../../../objects/enum/socialMedia";
import { useDataProvider } from "../../../../contexts/EntityPageDataProvider";
import { usePageContext } from "../../../../contexts/PageEntityProvider";
import { Filter } from "../../../../objects/class/tag/Filter";
import { CheckboxFormComponent } from "../../components/checkbox";
import { Tag } from "../../../../objects/class/tag/Tag";
import { FormTextInput } from "../../components/input/text";
import { FormFileInput } from "../../components/input/file";

interface EditComedianFormBodyProps {
    isLoading: boolean;
    form: any;
}

export default function EditComedianFormBody({
    isLoading,
    form,
}: EditComedianFormBodyProps) {
    const { filters } = useDataProvider();
    const { primaryEntity } = usePageContext();

    return (
        <div className="flex flex-row gap-2">
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
                <FormTextInput
                    key={"website"}
                    isLoading={isLoading}
                    name={"website"}
                    placeholder={"Website"}
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
            </div>
            <div className="flex flex-col gap-2">
                <CheckboxFormComponent
                    form={form}
                    items={filters
                        .filter(
                            (filter: Filter) => filter.type === primaryEntity,
                        )
                        .flatMap((filter: Filter) => filter.options)
                        .map((tag: Tag) => {
                            return {
                                id: tag.id,
                                displayName: tag.displayName,
                                value: tag.value,
                            };
                        })}
                />
            </div>
        </div>
    );
}
