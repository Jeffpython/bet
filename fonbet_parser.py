import time
from playwright.sync_api import sync_playwright, TimeoutError, Locator
from dataclasses import dataclass


@dataclass
class Game:
    team_1: str
    team_2: str
    league_id: int
    game_id: int
    minutes: int
    seconds: int
    score_1: int
    score_2: int

    def __repr__(self):
        return (f'{self.team_1} - {self.team_2} | '
                f'time {self.minutes}:{self.seconds} | '
                f'score {self.score_1}:{self.score_2}')


def remove_duplicates(games: list[Game]) -> list[Game]:
    temp = set()
    result = []
    for game in games:
        if game.game_id not in temp:
            temp.add(game.game_id)
            result.append(game)

    return result


class FonbetParser():
    def get_games(self) -> list[Game]:

        url = 'https://www.fon.bet/live/basketball'

        with sync_playwright() as playwright:

            # chromium - не скроллит блок (26.04.2024)
            # webkit - не скроллит блок и не корректно отображает страницу
            # firefox - скроллит блок, но глючит

            browser = playwright.firefox.launch(headless=False, slow_mo=500)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)

            time.sleep(2)

            games = []
            for game in self.get_games_with_duplicates(page):
                games.append(game)

            games = remove_duplicates(games)

            context.close()
            browser.close()

            return games

    def get_games_with_duplicates(self, page) -> list[Game]:

        while True:

            xpath_game = ('//span[contains(@class, "favorite-")]'
                          '/ancestor::div[contains(@data-testid, "sportBaseEvent.e_")]')

            for game in page.locator(xpath_game).all():
                team_1, team_2 = self.get_team_names(game)

                if team_1 is None or team_2 is None:
                    continue

                league_id, game_id = self.get_league_and_game_id(game)
                minutes, seconds = self.get_time(game)

                if minutes is None or seconds is None:
                    continue

                score_1, score_2 = self.get_score(game)

                yield Game(team_1=team_1,
                           team_2=team_2,
                           league_id=league_id,
                           game_id=game_id,
                           minutes=minutes,
                           seconds=seconds,
                           score_1=score_1,
                           score_2=score_2)

            xpath_last_game = '//*[contains(@data-testid, "sportBaseEvent.e_")][contains(@class, "_last")]'
            if page.locator(xpath_last_game).is_visible() is True:
                break

            xpath_header = '//*[contains(@class, "virtual-list--")] //*[contains(@class, "sport-section--")]'
            page.locator(xpath_header).click()
            page.keyboard.press('PageDown')

    def get_league_and_game_id(self, game: Locator) -> tuple[int, int]:
        link = game.get_by_test_id('event').get_attribute('href')
        league_id = int(link.split('/')[-3])
        match_id = int(link.split('/')[-2])
        return league_id, match_id

    def get_team_names(self, game: Locator) -> list[str] | list[None]:
        xpath = '//*[contains(@class, "sport-base-event__main")]//a'
        try:
            teams = game.locator(xpath).text_content(timeout=100)
            return teams.split(' — ')
        except TimeoutError:
            return [None, None]

        # если отображается не блок с игрой, а блок с победителями в плей-офф
        except AttributeError:
            return [None, None]

    def get_time(self, game: Locator) -> tuple[int, int] | tuple[None, None]:
        xpath = '//*[contains(@class, "event-block-current-time__time")]'

        try:
            time = game.locator(xpath).text_content(timeout=100)
            minutes = int(time.split(':')[0])
            seconds = int(time.split(':')[1])
            return minutes, seconds

        # игра еще не началась
        except TimeoutError:
            return None, None

    def get_score(self, game: Locator) -> tuple[int, int]:
        xpath = ('//*[contains(@class, "sport-base-event__main")]'
                 '//*[contains(@class, "event-block-score__score")]')
        score = game.locator(xpath).text_content()
        score_1 = int(score.split(':')[0])
        score_2 = int(score.split(':')[1])
        return score_1, score_2
