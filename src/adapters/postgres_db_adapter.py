# adapters/output/postgres/database_adapter.py

from src.domain.models.db_model import (
    BrandDataModel,
    CampaignDataModel,
)
from src.ports.input.db_port import BrandRepositoryPort
from .database import Database


class PostgresDatabaseAdapter(BrandRepositoryPort):
    def __init__(
        self,
        database: Database,
    ):
        self.database = database

    def get_by_id(
        self,
        brand_id: int,
    ) -> BrandDataModel | None:

        brand = self.database.fetch_one(
            """
            SELECT
                brand_id,
                brand_name,
                brand_description,
                brand_industry,
                brand_website
            FROM brands
            WHERE brand_id = %s
            """,
            (brand_id,),
        )

        if brand is None:
            return None

        campaigns = self.database.fetch_all(
            """
            SELECT
                brand_id,
                campaign_id,
                campaign_name,
                campaign_description,
                budget,
                success_rate,
                failure_rate,
                roi
            FROM campaigns
            WHERE brand_id = %s
            ORDER BY campaign_id
            """,
            (brand_id,),
        )

        return BrandDataModel(
            brand_id=brand["brand_id"],
            brand_name=brand["brand_name"],
            brand_description=brand["brand_description"],
            brand_industry=brand["brand_industry"],
            brand_website=brand["brand_website"],
            past_campaigns=[
                CampaignDataModel(**campaign)
                for campaign in campaigns
            ],
        )