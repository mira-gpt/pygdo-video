"""Duck animation keys and whether they persist by default."""

BASE_DEFAULTS = {
    key: key not in {'lol', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'turnaround'}
    for key in ('idle', 'quacking', 'sad', 'high', 'music', 'tipsy', 'drunk',
                'embarrassed', 'angry', 'inlove', 'trip', 'tired', 'lol', 'shrug',
                'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz', 'teacher', 'xd',
                'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king', 'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news', 'pirate', 'ghost')
}
