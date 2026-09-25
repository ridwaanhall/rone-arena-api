from enum import Enum

class LanguageEnum(str, Enum):
    '''Language codes for localized content.'''
    ENGLISH = "en"
    INDONESIAN = "id"
    RUSSIAN = "ru"
    SPANISH = "es"
    PORTUGUESE = "pt"
    TURKISH = "tr"
    ARABIC = "ar"
    GERMAN = "de"
    FRENCH = "fr"
    ITALIAN = "it"
    JAPANESE = "ja"
    KOREAN = "ko"
    THAI = "th"
    VIETNAMESE = "vi"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    KAMBODIAN = "km"
    
class RankEnum(str, Enum):
    '''Rank filter for hero statistics.'''
    ALL = "all"
    EPIC = "epic"
    LEGEND = "legend"
    MYTHIC = "mythic"
    HONOR = "honor"
    GLORY = "glory"

class SortOrderEnum(str, Enum):
    '''Sort order for query results.'''
    ASCENDING = "asc"
    DESCENDING = "desc"
    
class HeroRoleEnum(str, Enum):
    '''Enum for hero roles.'''
    TANK = "tank"
    FIGHTER = "fighter"
    ASSASSIN = "assassin"
    MAGE = "mage"
    MARKSMAN = "marksman"
    SUPPORT = "support"
    
class HeroLaneEnum(str, Enum):
    '''Enum for hero lanes.'''
    EXP = "exp"
    MID = "mid"
    ROAM = "roam"
    JUNGLE = "jungle"
    GOLD = "gold"


class VisibilityEnum(str, Enum):
    '''Visibility mode for user privacy setting update.'''
    VISIBLE = "visible"
    INVISIBLE = "invisible"


class WallpaperDeviceEnum(str, Enum):
    '''Target device for hero wallpapers.'''
    DESKTOP = "desktop"
    MOBILE = "mobile"
