from enum import Enum
from pydantic import BaseModel, Field


class CampaignGoal(str, Enum):
    BRAND_AWARENESS = "brand awareness"
    BUILDING_ENGAGEMENT = "building engagement"
    AUTHENTIC_CONTENT = "authentic content"


class PromotingItem(str, Enum):
    PHYSICAL_PRODUCT = "physical product"
    ONLINE_SERVICE = "online service"
    INSTORE_EXPERIENCE = "instore experience"


class CampaignNiche(str, Enum):
    FASHION_AND_BEAUTY = "fashion and beauty"
    LIFESTYLE = "lifestyle"
    GAMING_AND_ESPORTS = "gaming and esports"
    FOOD_AND_COOKING = "food & cooking"
    FITNESS_AND_WELLNESS = "fitness and wellness"
    EDUCATION_OR_SKILL = "education or skill"
    TRAVEL = "travel"
    TECH_AND_GADGETS = "tech & gadgets"
    PERSONAL = "personal"
    GADGETS = "gadgets"
    ART_OR_DIY = "art or diy"
    PET_PRODUCTS = "pet products"
    FAMILY_AND_PARENTING = "family and parenting"
    OTHERS = "others"
