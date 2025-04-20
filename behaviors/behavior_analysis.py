SESSION_BREAK_MS = 5000


def split_sessions(keystrokes):
    sessions = []
    current = []

    for k in keystrokes:
        if len(k["key"]) != 1:
            continue

        if not current:
            current.append(k)
        else:
            if k["timestamp"] - current[-1]["timestamp"] > SESSION_BREAK_MS:
                sessions.append(current)
                current = [k]
            else:
                current.append(k)

    if current:
        sessions.append(current)

    return sessions


def calculate_typing_speed(keystrokes):
    sessions = split_sessions(keystrokes)
    if not sessions:
        return 0

    last = sessions[-1]
    start_time = last[0]["timestamp"]
    end_time = last[-1]["timestamp"]

    time_diff_minutes = (end_time - start_time) / 60000
    char_count = len(last)
    words_typed = char_count / 5

    return words_typed / time_diff_minutes if time_diff_minutes > 0 else 0
