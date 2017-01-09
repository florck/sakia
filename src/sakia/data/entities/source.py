import attr


@attr.s()
class Source:
    currency = attr.ib(convert=str)
    pubkey = attr.ib(convert=str)
    identifier = attr.ib(convert=str)
    noffset = attr.ib(convert=int)
    type = attr.ib(convert=str, validator=lambda i, a, s: s == 'T' or s == 'D')
    amount = attr.ib(convert=int, cmp=False, hash=False)
    base = attr.ib(convert=int, cmp=False, hash=False)
