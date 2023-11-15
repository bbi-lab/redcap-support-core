from pydantic import BaseModel as PydanticBaseModel, field_validator, ConfigDict
from pydantic.alias_generators import to_camel


class BaseModel(PydanticBaseModel):
    @field_validator("*", mode="before")
    def empty_str_to_none(cls, x):
        """
        Convert empty strings to None. This is applied to all string-valued attributes before other validators run.

        :param x: The attribute value
        :return: None if x was the empty string, otherwise x
        """
        if x == "":
            return None
        return x

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
