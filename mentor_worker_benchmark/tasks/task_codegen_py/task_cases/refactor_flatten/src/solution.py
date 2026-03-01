def flatten(nested: list[object] | tuple[object, ...], acc: list[object] = []) -> list[object]:
    for item in nested:
        if isinstance(item, list):
            flatten(item, acc)
        else:
            acc.append(item)
    return acc
