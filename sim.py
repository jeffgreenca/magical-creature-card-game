from nicegui import ui, app
from dataclasses import dataclass
from typing import List
import random

@dataclass
class Card:
    title: str
    kind: str
    subcategory: str
    text: str
    image: str
    id: str = ""

    def __post_init__(self):
        """Generate a random ID 8 characters a-z"""
        self.id = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8))

@dataclass
class Stack:
    """Any stack of cards. It could be a deck, a hand, a discard pile, etc."""
    cards: List[Card]

    def draw(self):
        return self.cards.pop()
    
    def shuffle(self):
        x = list(self.cards)
        random.shuffle(x)
        self.cards = x

    def add_to_top(self, card):
        self.cards.append(card)
    
    def add_to_bottom(self, card):
        self.cards.insert(0, card)

@dataclass
class Player:
    name: str
    hand: Stack
    completedQuests: Stack
    treasure: Stack
    tokens: int

@dataclass
class Game:
    players: list[Player]
    deck: Stack
    discard: Stack
    treasureDeck: Stack
    treasureDiscard: Stack
    currentPlayer: int = 0
    maxTokens: int = 10
    selectedCard: Card = None

# TODO
# load cards from CSV, and while loading, organize them into decks:
# - KIND resource, quest, event go into game.deck
# - KIND treasure goes into game.treasureDeck
# set up to play by shuffling and dealing cards to players


# probably the easiest is to just lay out all the cards on the "table"
# and then allow drag and drop anywhere on the screen
# with a toggle to show/hide the opposing player(s) cards

# this is probably the easiest for rapid prototyping

def load_cards(file="cards.csv"):
    # load cards from CSV
    import csv
    cards = []
    with open(file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            count = int(row.pop('count', 1))
            for _ in range(count):
                cards.append(Card(**row))
    return cards

def init_game():
    NUM_INITIAL_CARDS = 5

    all_cards = load_cards()
    # build the deck and treasure deck
    deck = Stack((x for x in all_cards if x.kind in ("resource", "quest", "event")))
    treasureDeck = Stack((x for x in all_cards if x.kind == "treasure"))
    # shuffle the decks
    deck.shuffle()
    treasureDeck.shuffle()

    players = []
    for i in (1, 2):
        hand = Stack([deck.draw() for _ in range(NUM_INITIAL_CARDS)])
        player = Player(f"Player {i}", hand, Stack([]), Stack([]), 0)
        players.append(player)

    return Game(players, deck, Stack([]), treasureDeck, Stack([]))

def ui_gamecard(card):
    with ui.card().style("width: 10em; height: 15em;"):
        if card.image:
            ui.image(card.image)
        ui.label(card.title)
        ui.label(card.kind)
        ui.label(card.subcategory)
        ui.label(card.text).classes("text-xs")

@ui.refreshable
def ui_player(player, mirror=False):
    if mirror:
        _ui_player_visible_cards(player)
        _ui_player_hand(player)
    else:
        _ui_player_hand(player)
        _ui_player_visible_cards(player)

def _ui_player_hand(player):
    with ui.row().style("border: 1px solid red;"):
        with ui.column():
            ui.label(f"{player.name}'s Hand")
            with ui.row():
                for card in player.hand.cards:
                    ui_gamecard(card)

def _ui_player_visible_cards(player):
    with ui.row().style("border: 1px solid blue;"):
        with ui.row():
            with ui.column():
                ui.label(f"{player.name}'s Completed Quests")
                for card in player.completedQuests.cards:
                    ui_gamecard(card)
            with ui.column().style("border-left: 1px solid blue;"):
                ui.label(f"{player.name}'s Treasure")
                for card in player.treasure.cards:
                    ui_gamecard(card)

backside_card = Card("Game Card", "", "", "", "")
discard_card = Card("Discard", "", "", "", "")

@ui.refreshable
def ui_common(game):
    with ui.row().classes("w-full").style("border: 1px solid blue;"): #.classes("mx-auto justify-between w-1/2"):
        with ui.column().classes("w-1/4").style("border: 1px solid green;"):
            ui.label("Deck")
            with ui.row():
                ui_gamecard(backside_card)
                if len(game.discard.cards) > 0:
                    ui_gamecard(game.discard.cards[-1])
                else:
                    ui_gamecard(discard_card)
        with ui.column():
            ui.space()
        with ui.column().classes("w-1/4").style("border: 1px solid green;"):
            ui.label("Treasure")
            with ui.row():
                ui_gamecard(backside_card)
                if len(game.treasureDiscard.cards) > 0:
                    ui_gamecard(game.treasureDiscard.cards[-1])
                else:
                    ui_gamecard(discard_card)

if __name__ in ("__main__", "__mp_main__"):
    game = init_game()

    # top row: player 1 hand
    # next row: player 1 completed quests, player 1 treasure (2 columns)
    # next row: game deck, game discard, game treasure deck, game treasure discard
    # next row: player 2 treasure and player 2 completed quests (2 columns)
    # bottom row: player 2 hand

    ui_player(game.players[0])
    ui_common(game)
    ui_player(game.players[1], mirror=True)

    def reset_game():
        global game
        game = init_game()
        ui_player.refresh(game.players[0])
        ui_player.refresh(game.players[1])
        ui_common.refresh(game)

    ui.button("Reset Game", on_click=reset_game)


    ui.run()
