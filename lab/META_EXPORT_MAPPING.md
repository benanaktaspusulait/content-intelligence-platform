# Meta Export Mapping

The versioned alias mapper recognises common Meta labels such as Content ID/Post ID, publication time, reach, video views, 3-second views, minutes viewed, average watch time, reactions/likes, comments, shares, saves, and follows.

Aliases map only when their semantics are defensible. `Plays` may map to views only in a known export schema; unknown schemas retain the raw column and emit a warning. Country breakdown sheets are retained even when they cannot yet be joined automatically.

