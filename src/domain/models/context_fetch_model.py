from typing import List

from pydantic import BaseModel, Field

class SearchWebsites(BaseModel):
    title: str = Field(...,description="Title")
    url: str = Field(...,description="URL")
    headings:str = Field(...,description="Headings")
    description: str = Field(...,description="Description")



class RetrievedContextModel(BaseModel):
    title: str = Field(...,description="Title")
    context: str = Field(...,description="The detailed content, text, or trends extracted from the search result.")
    url: str = Field(None, description="The URL of the search result.")

class RetrievedContextList(BaseModel):
    contexts: list[RetrievedContextModel] = Field(default_factory=list)

class TopKWebsites(BaseModel):
    websites: List[SearchWebsites] = Field(...,description="Websites")


class AggregatedContextModel(BaseModel):
    context_id: str = Field(...,description="Context ID")
    context: str= Field(...,description="Context")


