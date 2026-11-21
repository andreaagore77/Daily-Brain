"""Keyword rules that sort tasks into categories, plus a helper that
splits a spoken or typed "brain dump" into separate tasks."""

import re

# Built-in categories. Each has a list of keywords. Categories are
# checked in this order, and the first match wins. A person's own
# custom categories are checked BEFORE these (see categorize below).
CATEGORIES = {
    "School": ["exam", "homework", "study", "class", "lecture",
               "assignment", "quiz", "professor"],
    "Business": ["invoice", "client", "order", "product", "grant",
                 "funding", "sponsor"],
    "Health & Wellness": ["doctor", "dentist", "appointment", "checkup",
                          "therapy", "pharmacy", "prescription", "workout",
                          "gym", "yoga", "meditate", "vitamins"],
    "Work": ["meeting", "shift", "report", "email", "deadline",
             "project", "call"],
}

# Not a starting point: a task only lands here if NO keyword list matches.
DEFAULT_CATEGORY = "Personal"


def matches(task, keyword):
    """True if the keyword appears in the task as a whole word.

    "recall" does NOT count as "call". Simple plurals do count:
    "exams" matches "exam" and "classes" matches "class".
    """
    # \b means "word boundary"; (s|es)? allows an optional plural ending.
    pattern = r"\b" + re.escape(keyword.lower()) + r"(s|es)?\b"
    return re.search(pattern, task.lower()) is not None


def categorize(task, custom_categories=None):
    """Return the category for one task.

    custom_categories is a list like
        [{"name": "Kids", "keywords": ["soccer", "daycare"]}]
    Custom categories are checked first, so a person's own rules win.
    """
    rules = [(c["name"], c["keywords"]) for c in (custom_categories or [])]
    rules += list(CATEGORIES.items())
    for category, keywords in rules:
        if any(matches(task, keyword) for keyword in keywords):
            return category
    return DEFAULT_CATEGORY


# Filler phrases people say out loud before a task. Longer phrases come
# first so "ok so" is removed as a whole before "ok" is checked.
FILLER_STARTS = [
    "don't forget to", "i've got to", "remember to", "i need to",
    "i have to", "i should", "i gotta", "let's add", "lets add",
    "and then", "okay so", "ok so", "k so", "as well as",
    "and", "then", "also", "plus", "okay", "ok", "so", "k", "um", "uh",
]

# Short titles that end with a period but don't end a sentence.
ABBREVIATIONS = r"\b(dr|mr|mrs|ms|prof|st|appt)\."


def clean_task(text):
    """Trim spaces, punctuation and filler words from the start of a task."""
    task = text.replace("’", "'").strip(" .,;!?\t\n")
    changed = True
    while changed:  # repeat, so "ok so let's add ..." is fully cleaned
        changed = False
        for filler in FILLER_STARTS:
            if task.lower() == filler:
                return ""  # the whole piece was just filler, e.g. "ok"
            if task.lower().startswith(filler + " "):
                task = task[len(filler):].strip(" .,;!?")
                changed = True
                break
    # Capitalize the first letter so the list looks neat.
    return task[:1].upper() + task[1:]


def word_count(text):
    return len(clean_task(text).split())


def split_on_and(piece):
    """Split on "and" only when BOTH sides have at least 2 words.

    "email my professor and call mom" -> 2 tasks
    "buy salt and pepper"             -> stays 1 task
    """
    parts = re.split(r"\s+and\s+", piece, flags=re.IGNORECASE)
    tasks = [parts[0]]
    for part in parts[1:]:
        if word_count(tasks[-1]) >= 2 and word_count(part) >= 2:
            tasks.append(part)
        else:
            tasks[-1] = tasks[-1] + " and " + part  # keep them together
    return tasks


def split_tasks(brain_dump, keep_together=()):
    """Turn one block of text into a list of separate tasks.

    Splits on new lines, commas, semicolons, sentence-ending periods,
    "as well as", and (carefully) "and".

    keep_together is a person's own list of phrases that must never be
    split, like "lemon pepper and garlic blend".

    Example:
        "ok so study for my exam, email my professor and pick up groceries"
        -> ["Study for my exam", "Email my professor", "Pick up groceries"]
    """
    text = brain_dump.replace("’", "'")

    # 1. Protect the person's keep-together phrases by swapping each one
    #    for a placeholder that contains nothing we split on.
    protected = {}
    for i, phrase in enumerate(p.strip() for p in keep_together if p.strip()):
        placeholder = f"KEEPTOGETHER{i}X"
        text, count = re.subn(re.escape(phrase), placeholder, text,
                              flags=re.IGNORECASE)
        if count:
            protected[placeholder] = phrase

    # 2. "Dr. Smith" shouldn't be split at the period, so hide that
    #    period for now and put it back at the end.
    text = re.sub(ABBREVIATIONS, r"\1ABBRDOT", text, flags=re.IGNORECASE)

    # 3. Split into pieces.
    pieces = re.split(r"[\n,;]+|\.(?=\s|$)|\bas well as\b", text,
                      flags=re.IGNORECASE)
    tasks = []
    for piece in pieces:
        for task in split_on_and(piece):
            # 4. Put the protected phrases back.
            for placeholder, phrase in protected.items():
                task = task.replace(placeholder, phrase)
            task = clean_task(task.replace("ABBRDOT", "."))
            if task:
                tasks.append(task)
    return tasks
