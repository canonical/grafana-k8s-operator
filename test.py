from dataclasses import dataclass


@dataclass
class App:
    name: str = None


class Relation:
    def __init__(self, app=None):
        if app:
            self.app = app
        else:
            self.app = None


if __name__ == "__main__":
    r = Relation()
    r2 = Relation(App())
    r3 = Relation(App("foo"))

    if not all([x for x in [r, r.app, r2.app.name]]):
        # if not r or not r.app or not r.app.name:
        print("BOOM!!")
    else:
        print(r)
        print(r.app)
        print(r2.app.name)
