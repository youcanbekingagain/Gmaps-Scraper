GMAPS_SEARCH_BAR = "#searchboxinput"
RESULT_ONE_BY_ONE = "//div[@role='feed']/*"
RESULT_BOX_DIV = "//div[@role='feed']/*[last()]"
RESULT_BOX_DIV_SECOND_LAST = "//div[@role='feed']/*[last()-1]"
RESULT_URLS = "//div[@role='feed']//div//a[contains(@href, '/place/')]"
PLACE_NAME = "//h1"
PLACE_REVIEW_STAR = (
    "//span[@role='img' and contains(@aria-label, 'stars')]/preceding-sibling::span[1]"
)
PLACE_REVIEW_PEOPLE_NUMBER = "//span[@aria-label[contains(., 'reviews')]]"
PLACE_TYPE = "(//h1/following::div[1]//button)[1]"
PLACE_ADDRESS = "(//button[@data-item-id = 'address']//div)[4]"
PLACE_WEBSITE = "(//*[@aria-label[contains(., 'Website')]]//div)[4]"
PLACE_PHONE = "(//*[@aria-label[contains(., 'Phone')]]//div)[4]"
PLACE_PLUS_CODE = "(//button[@aria-label[contains(., 'Plus code')]]//div)[4]"
PLACE_IMG = "//div[@aria-label[contains(.,'Photos of')] and @aria-roledescription = 'carousel']//img"

SCROLLING_EVERY_SEARCH = (
    "(//div[@jsaction = 'focus:scrollable.focus; blur:scrollable.blur'])[6]"
)

WEB_SEARCH_RESULTS = "//body//div[@role='button']//span[@role='text']"
