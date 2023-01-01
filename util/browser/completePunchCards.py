import logging

import util

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
import time
from util import deprecated


@deprecated
def completePunchCards(browser: WebDriver, BASE_URL: str):
    punchCards = util.getDashboardData(browser)['punchCards']
    for punchCard in punchCards:
        try:
            if punchCard['parentPromotion'] != None and punchCard['childPromotions'] != None and \
                    punchCard['parentPromotion']['complete'] == False and punchCard['parentPromotion'][
                'pointProgressMax'] != 0:
                if BASE_URL == "https://rewards.microsoft.com":
                    util.completePunchCard(browser, punchCard['parentPromotion']['attributes']['destination'],
                                           punchCard['childPromotions'])
                else:
                    url = punchCard['parentPromotion']['attributes']['destination']
                    path = url.replace(
                        'https://account.microsoft.com/rewards/dashboard/', '')
                    userCode = path[:4]
                    dest = 'https://account.microsoft.com/rewards/dashboard/' + \
                           userCode + path.split(userCode)[1]
                    util.completePunchCard(browser, url, punchCard['childPromotions'])
        except:
            util.resetTabs(browser, BASE_URL=BASE_URL)
    time.sleep(2)
    browser.get(BASE_URL)
    time.sleep(2)


def complete_punch_cards(browser: WebDriver, base_url: str):
    logger: logging.Logger = logging.getLogger("msrf")  # get logger
    punchCards = util.getDashboardData(browser)['punchCards']
    for punchCard in punchCards:
        try:
            if punchCard['parentPromotion'] != None and \
                    punchCard['childPromotions'] != None and \
                    punchCard['parentPromotion']['complete'] == False and \
                    punchCard['parentPromotion']['pointProgressMax'] != 0:
                if base_url == "https://rewards.microsoft.com":
                    logger.info("Completing single punch card")
                    util.complete_punch_card(browser, punchCard['parentPromotion']['attributes']['destination'],
                                           punchCard['childPromotions'])
                else:
                    url = punchCard['parentPromotion']['attributes']['destination']
                    path = url.replace(
                        'https://account.microsoft.com/rewards/dashboard/', '')
                    userCode = path[:4]
                    dest = 'https://account.microsoft.com/rewards/dashboard/' + \
                           userCode + path.split(userCode)[1]
                    util.complete_punch_card(browser, url, punchCard['childPromotions'])
        except Exception as e:
            logger.critical(f"Uncaught exception in completing punch cards. Likely malformed data. Resetting tabs. {e}")
            util.resetTabs(browser, BASE_URL=base_url)
    time.sleep(2)
    logger.info("Returning home.")
    browser.get(base_url)
    time.sleep(2)
