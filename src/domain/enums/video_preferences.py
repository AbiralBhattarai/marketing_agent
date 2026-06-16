from enum import Enum
class VideoOrientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    SQUARE = "square"


class VideoType(str, Enum):
    BEFORE_AFTER = "before/after"
    INFORMATION = "information"
    LIFESTYLE = "lifestyle"
    REVIEWS = "reviews"
    PRODUCT_DEMO = "product demo"
    RECIPES = "recipes"
    TESTIMONIALS = "testimonials"
    TUTORIALS = "tutorials"
    UNBOXING = "unboxing"


class VideoDuration(str, Enum):
    FIFTEEN_SECONDS = "15s"
    THIRTY_SECONDS = "30s"
    SIXTY_SECONDS = "60s"
    ONE_TO_FIVE_MINS = "1-5m"
    MORE_THAN_FIVE_MINS = ">5m"

#video script lai api call.


