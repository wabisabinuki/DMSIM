"""Base class for temporary continuous effects attached to a card."""

from effects.base.duration_effect import DurationEffect


class EnchantEffect(DurationEffect):
    """A duration effect that attaches itself to a target card."""

    attachment_attr = None

    def __init__(
        self,
        source_card,
        target_card,
        duration_type,
        game,
        duration_turns=0,
        attachment_attr=None,
    ):
        super().__init__(
            source_card=source_card,
            duration_type=duration_type,
            game=game,
            duration_turns=duration_turns,
        )
        self.target_card = target_card
        self.owner_card = source_card
        self.granted_card = target_card
        self.granted_zone = getattr(
            target_card,
            "zone",
            None,
        )
        self.attachment_attr = (
            attachment_attr
            if attachment_attr is not None
            else self.attachment_attr
        )

    def can_resolve(
        self,
        game_state,
    ):
        return self.target_card is not None

    def resolve(
        self,
    ):
        if self.target_card is None:
            return False

        self.attach()
        self.register_duration()
        self.is_active = True
        self.register_with_duration_manager()
        return True

    def attach(
        self,
    ):
        if self.attachment_attr is not None:
            attachments = getattr(
                self.target_card,
                self.attachment_attr,
                None,
            )
            if attachments is None:
                attachments = []
                setattr(
                    self.target_card,
                    self.attachment_attr,
                    attachments,
                )

            if self not in attachments:
                attachments.append(self)

        self.on_attach()

    def detach(
        self,
    ):
        if self.attachment_attr is None:
            return

        attachments = getattr(
            self.target_card,
            self.attachment_attr,
            [],
        )
        if self in attachments:
            attachments.remove(self)

    def transfer_to(
        self,
        target_card,
    ):
        if target_card is self.target_card:
            return

        self.detach()
        self.target_card = target_card
        self.attach()

    def unapply(
        self,
    ):
        self.detach()
        self.on_detach()
        super().unapply()

    def register_with_duration_manager(
        self,
    ):
        manager = getattr(
            self.game,
            "duration_effect_manager",
            None,
        )
        if manager is not None:
            manager.register_duration_effect(self)

    def on_attach(
        self,
    ):
        return None

    def on_detach(
        self,
    ):
        return None
