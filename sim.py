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
    selected: bool = False

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

    def remove(self, card):
        """Remove a card from anywhere in the stack."""
        self.cards.remove(card)


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
    selected: Card = None

    def deselect_card(self):
        if self.selected:
            self.selected.selected = False
            self.selected = None

    def select_card(self, card):
        self.deselect_card()
        self.selected = card
        self.selected.selected = True

    def move_card(self, card, destination):
        self.find_stack(card).cards.remove(card)
        destination.add_to_top(card)
        if self.is_selected(card):
            # this is a nice UX thing
            self.deselect_card()

    def find_stack(self, card):
        for player in self.players:
            for stack in (player.hand, player.completedQuests, player.treasure):
                if card in stack.cards:
                    return stack
        for stack in (self.deck, self.discard, self.treasureDeck, self.treasureDiscard):
            if card in stack.cards:
                return stack

    def is_selected(self, card):
        return self.selected and self.selected.id == card.id

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

def ui_gamecard(card, on_click_cb=None, visible=True):
    def click():
        if on_click_cb:
            on_click_cb(card)
    additionalStyles = "border: 1px solid green;" if card.selected else ""
    with ui.card().style(f"width: 10em; height: 15em; {additionalStyles}").on("click", click):
        if visible or card.selected:
            ui.badge(card.kind).classes("ml-auto")
            ui.label(card.title)
            if card.image:
                ui.image(card.image)
            if card.subcategory:
                ui.label(card.subcategory)
            ui.label(card.text).classes("text-xs")
        else:
            ui.space()
            ui.icon("star", size="1em").classes("mx-auto")
            ui.space()

def ui_player(game, player_idx, select_card_cb, click_hand_cb, mirror=False):
    player = game.players[player_idx]
    if mirror:
        _ui_player_visible_cards(player, select_card_cb)
        _ui_player_hand(player, select_card_cb, click_hand_cb)
    else:
        _ui_player_hand(player, select_card_cb, click_hand_cb)
        _ui_player_visible_cards(player, select_card_cb)

def _ui_player_hand(player, cb, hand_cb=None):
    with ui.row().style("border: 1px solid red;"):
        with ui.column():
            ui.label(f"{player.name}'s Hand")
            with ui.row().classes("items-center"):
                ui.icon("front_hand", size="xl").on("click", hand_cb)
                for card in reversed(player.hand.cards):
                    ui_gamecard(card, cb)

def _ui_player_visible_cards(player, cb):
    with ui.row().style("border: 1px solid blue;"):
        with ui.row():
            with ui.column():
                ui.label(f"{player.name}'s Completed Quests")
                for card in player.completedQuests.cards:
                    ui_gamecard(card, cb)
            with ui.column().style("border-left: 1px solid blue;"):
                ui.label(f"{player.name}'s Treasure")
                for card in player.treasure.cards:
                    ui_gamecard(card, cb)

backside_card = Card("Game Card", "", "", "", "")
discard_card = Card("Discard", "", "", "", "")
empty_card = Card("", "", "", "", "")

@ui.refreshable
def ui_common(game, deck_click_cb=None, discard_click_cb=None, treasure_click_cb=None, treasure_discard_click_cb=None):
    with ui.row().classes("w-full").style("border: 1px solid blue;"): #.classes("mx-auto justify-between w-1/2"):
        with ui.column().classes("w-1/4").style("border: 1px solid green;"):
            ui.label("Deck")
            with ui.row():
                # face-down main deck
                if len(game.deck.cards) > 0:
                    ui_gamecard(game.deck.cards[-1], deck_click_cb, visible=False)
                else:
                    ui_gamecard(empty_card) # TODO - shuffle discard back into deck

                # face-up discard pile
                if len(game.discard.cards) > 0:
                    ui_gamecard(game.discard.cards[-1], discard_click_cb)
                else:
                    ui_gamecard(discard_card, discard_click_cb)
        with ui.column():
            ui.space()
        with ui.column().classes("w-1/4").style("border: 1px solid green;"):
            ui.label("Treasure")
            with ui.row():
                if len(game.treasureDeck.cards) > 0:
                    ui_gamecard(game.treasureDeck.cards[-1], treasure_click_cb, visible=False)
                else:
                    ui_gamecard(empty_card) # TODO - shuffle treasure discard back into deck

                if len(game.treasureDiscard.cards) > 0:
                    ui_gamecard(game.treasureDiscard.cards[-1], treasure_discard_click_cb)
                else:
                    ui_gamecard(discard_card, treasure_discard_click_cb)

def notify(msg):
    ui.notify(msg, position="center", type='warning', timeout=500, animation=False)

if __name__ in ("__main__", "__mp_main__"):
    game = init_game()

    # this is an annoying hack
    # the refreshable decorator is not working as I expect on repeated calls with different arguments
    # so wrapping the calls in functions which can be refreshed
    # this additional layer of indirection seems to work
    def render_ui_player(i):
        mirror = i == 1
        ui_player(game=game, player_idx=i, select_card_cb=select_card, click_hand_cb=make_select_hand_cb(i), mirror=mirror)

    @ui.refreshable
    def p1():
        i = 0
        render_ui_player(i)

    @ui.refreshable
    def p2():
        i = 1
        render_ui_player(i)

    def refresh_all():
        p1.refresh()
        ui_common.refresh(game=game, discard_click_cb=discard_cb, treasure_discard_click_cb=treasure_discard_cb)
        p2.refresh()

    def select_card(card):
        if game.is_selected(card):
            game.deselect_card()
        else:
            game.select_card(card)
        refresh_all()

    def make_select_hand_cb(player_idx):
        def select_hand(_):
            if game.selected:
                game.move_card(game.selected, game.players[player_idx].hand)
                refresh_all()
        return select_hand

    def make_select_stack_cb(stack_name, allowed_kinds):
        def select_stack(_):
            # game reset will mess up our reference to the stack
            # so we wrap the stack reference
            stack = getattr(game, stack_name)
            # if a card is selected, move it to the discard pile
            # keep it selected in case we want to move it back
            # otherwise, select the top discard card if present
            top_discard = None
            if len(stack.cards) > 0:
                top_discard = stack.cards[-1]

            if top_discard and game.is_selected(top_discard):
                # clicking on the top discard which we already selected
                game.deselect_card()
            elif game.selected:
                # clicking on discard with some other card selected
                if not game.selected.kind in allowed_kinds:
                    notify(f"You can't place a {game.selected.kind} card there")
                    return
                game.move_card(game.selected, stack)
            else:
                # no card selected, select the top discard card
                if top_discard:
                    game.select_card(top_discard)

            # finally
            refresh_all()
        return select_stack

    deck_cb = make_select_stack_cb("deck", ("resource", "quest", "event"))
    treasure_cb = make_select_stack_cb("treasureDeck", ("treasure",))
    discard_cb = make_select_stack_cb("discard", ("resource", "quest", "event"))
    treasure_discard_cb = make_select_stack_cb("treasureDiscard", ("treasure",))


    p1()
    ui_common(game=game, deck_click_cb=deck_cb, discard_click_cb=discard_cb, treasure_click_cb=treasure_cb, treasure_discard_click_cb=treasure_discard_cb)
    p2()

    def reset_game():
        global game
        game = init_game()
        refresh_all()

    ui.button("New Game", on_click=reset_game)

    ui.run()
