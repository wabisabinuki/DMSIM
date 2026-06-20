"""
ゲーム内イベント（召喚、破壊、領域移動等）の購読（Subscribe）および発行（Publish）を担うイベントハブ。
"""

from collections import defaultdict

from ui.debug_log import debug_print


class EventManager:

    def __init__(self):

        # event_type -> listeners
        self.listeners = defaultdict(list)

    def subscribe(
        self,
        event_type,
        listener,
    ):

        listeners = (
            self.listeners[event_type]
        )

        # Extract ability and card info from listener
        ability_name = "unknown"
        card_name = "unknown"
        
        if hasattr(listener, '__self__'):
            ability_obj = listener.__self__
            ability_name = (
                ability_obj.__class__.__name__
            )
            if hasattr(
                ability_obj,
                'owner_card'
            ):
                card_name = (
                    ability_obj.owner_card.name
                )

        if listener in listeners:
            debug_print(
                f"[SUBSCRIBE] "
                f"event_type={event_type.__name__}, "
                f"ability={ability_name}, "
                f"card={card_name}, "
                f"status=ALREADY_REGISTERED"
            )
            return

        self.listeners[event_type].append(
            listener
        )

        debug_print(
            f"[SUBSCRIBE] "
            f"event_type={event_type.__name__}, "
            f"ability={ability_name}, "
            f"card={card_name}, "
            f"status=REGISTERED"
        )

    def unsubscribe(
        self,
        event_type,
        listener,
    ):
        
        debug_print(
            f"[UNSUBSCRIBE] "
            f"{listener}"
        )

        if listener in self.listeners[event_type]:

            self.listeners[event_type].remove(
                listener
            )

    def get_listeners(
        self,
        event_type,
    ):

        return list(
            self.listeners[event_type]
        )

    def publish(self, event):

        debug_print(
            f"[EVENT] {event}"
        )

        event_type = type(event)

        listeners = self.listeners[event_type]

        for listener in listeners[:]:

            listener(event)
