from fonbet_parser import FonbetParser


def main():
    parser = FonbetParser()
    games = parser.get_games()

    for game in games:
        print(game)


if __name__ == '__main__':
    main()
