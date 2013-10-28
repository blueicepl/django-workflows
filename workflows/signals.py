import django.dispatch


before_state_change = django.dispatch.Signal(providing_args=["from_state", "to_state"])
after_state_change = django.dispatch.Signal(providing_args=["from_state", "to_state"])

before_transition = django.dispatch.Signal(providing_args=["from_state", "transition", "user"])
after_transition = django.dispatch.Signal(providing_args=["from_state", "transition", "user"])
