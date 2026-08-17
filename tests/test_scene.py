from app.scene import Scene


def test_construction_stores_the_game_reference():
    game = object()
    scene = Scene(game)
    assert scene.game is game


def test_default_hooks_are_no_ops():
    scene = Scene(object())

    # None of these should raise or return anything meaningful -- subclasses
    # override the ones they care about.
    assert scene.on_enter() is None
    assert scene.on_exit() is None
    assert scene.handle_event(None) is None
    assert scene.update() is None
    assert scene.draw() is None
