from core.deleter import delete_item


def delete_many(paths):
    ok = 0
    fail = 0
    for path in paths:
        if delete_item(path):
            ok += 1
        else:
            fail += 1
    return ok, fail
