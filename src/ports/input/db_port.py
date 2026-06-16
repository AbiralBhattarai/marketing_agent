# ports/output/user_repository_port.py

from abc import ABC, abstractmethod
from src.domain.models.db_model import BrandDataModel


class BrandRepositoryPort(ABC):

    @abstractmethod
    def get_by_id(
        self,
        brand_id: int
    ) -> BrandDataModel | None:
        pass