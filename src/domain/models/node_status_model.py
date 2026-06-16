from pydantic import BaseModel, Field

class NodeStatusModel(BaseModel):
    is_executed: bool = Field(
        default=False, 
        description="Indicates whether the node has been successfully executed."
    )
    retry_count: int = Field(
        default=0, 
        ge=0, 
        le=3, 
        description="Number of retries attempted for this node. Maximum allowed is 3."
    )
