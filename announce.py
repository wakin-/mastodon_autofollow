from mastodon import Mastodon

from Zodiac import Zodiac

def announce(user_id, domain, zodiac_id):
    zodiac = Zodiac.first(id=zodiac_id)
    if zodiac.bot_access_token is '' or zodiac.bot_access_token is None or zodiac.bot_base_url is '' or zodiac.bot_base_url is None:
        return
    bot = Mastodon(access_token=zodiac.bot_access_token, api_base_url=zodiac.bot_base_url)
    status = '%s@%s が参加しました！' % (user_id, domain)
    bot.status_post(status=status, visibility='unlisted')
