"""Daily Brain: a mobile-friendly web app that sorts your to-dos.

Type or talk your list (use your phone keyboard's mic button), and
Daily Brain splits it into tasks and sorts each one into School,
Business, Health & Wellness, Work, Personal, or a category you create.

Everything saves automatically in the person's own browser, so
closing the page by accident doesn't lose anything, and no one's
tasks are ever stored on a server.

Run it with:  streamlit run app.py
"""

import json
import uuid
from datetime import date

import streamlit as st

from categories import CATEGORIES, DEFAULT_CATEGORY, categorize, split_tasks

BUILT_IN_ICONS = {"School": "📚", "Business": "💼", "Health & Wellness": "🩺",
                  "Work": "🗂️", "Personal": "🏡"}
ICON_CHOICES = ["📌", "⭐", "🎯", "🎨", "🐾", "👶", "🏠", "💰", "✈️", "🙏"]

st.set_page_config(page_title="Daily Brain")

# ---------- Saving in the browser ----------
# A tiny piece of JavaScript that reads and writes the browser's
# localStorage: a small storage space every browser gives each website.
# The data stays on the person's own phone or computer.
STORAGE_JS = """
export default function(component) {
    const { data, setStateValue } = component;
    const KEY = "daily-brain";
    try {
        if (data && data.mode === "save") {
            window.localStorage.setItem(KEY, data.value);
        } else {
            setStateValue("saved", window.localStorage.getItem(KEY) || "");
        }
    } catch (error) {
        // Some private-browsing modes block storage. Start fresh instead.
        if (!(data && data.mode === "save")) setStateValue("saved", "");
    }
}
"""
browser_storage = st.components.v2.component("daily_brain_storage", js=STORAGE_JS)


def empty_state():
    return {"tasks": [], "custom_categories": [], "keep_together": []}


def load_from_browser():
    """On first visit, read the saved list. Stops the page until it arrives."""
    result = browser_storage(data={"mode": "load"}, key="storage_load",
                             on_saved_change=lambda: None)
    saved = getattr(result, "saved", None)
    if saved is None:
        st.caption("Loading your list…")
        st.stop()  # the browser will answer in a moment and the page reloads
    state = empty_state()
    if saved:
        try:
            state.update(json.loads(saved))
        except json.JSONDecodeError:
            pass  # damaged data: start with an empty list
    st.session_state.update(state)
    st.session_state.loaded = True


def save_to_browser():
    """Write everything back to the browser. Runs at the end of every page update."""
    snapshot = {k: st.session_state[k] for k in empty_state()}
    browser_storage(data={"mode": "save", "value": json.dumps(snapshot)},
                    key="storage_save")


if not st.session_state.get("loaded"):
    load_from_browser()


# ---------- Helpers ----------
def all_categories():
    """The person's own categories, then the built-in ones, then Personal."""
    custom = [c["name"] for c in st.session_state.custom_categories]
    return custom + list(CATEGORIES) + [DEFAULT_CATEGORY]


def icon_for(category):
    for c in st.session_state.custom_categories:
        if c["name"] == category:
            return c["icon"]
    return BUILT_IN_ICONS.get(category, "📌")


def resort_tasks():
    """Re-sort every task the person hasn't moved by hand."""
    for t in st.session_state.tasks:
        if not t.get("moved"):
            t["category"] = categorize(t["task"], st.session_state.custom_categories)


def move_task(task_id, menu_key):
    """Runs when the person picks a new category from the ⋯ menu."""
    for t in st.session_state.tasks:
        if t["id"] == task_id:
            t["category"] = st.session_state[menu_key]
            t["moved"] = True  # remember the person chose this, so re-sorting leaves it alone


def delete_task(task_id):
    st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] != task_id]


def handle_brain_dump():
    """Runs when the person taps 'Sort my tasks'."""
    texts = split_tasks(st.session_state.brain_dump, st.session_state.keep_together)
    for text in texts:
        st.session_state.tasks.append({
            "id": str(uuid.uuid4()),
            "task": text,
            "category": categorize(text, st.session_state.custom_categories),
            "done": False,
            "moved": False,
            "added": date.today().isoformat(),
        })
    st.session_state.message = f"Added {len(texts)} task(s)." if texts else "Nothing to add yet."
    st.session_state.brain_dump = ""  # clear the box for the next list


def handle_new_category():
    """Runs when the person taps 'Add category'."""
    name = st.session_state.new_cat_name.strip()
    keywords = [k.strip() for k in st.session_state.new_cat_keywords.split(",") if k.strip()]
    taken = [c.lower() for c in all_categories()]
    if not name:
        st.session_state.cat_error = "Give your category a name."
    elif name.lower() in taken:
        st.session_state.cat_error = f'You already have a category called "{name}".'
    elif not keywords:
        st.session_state.cat_error = "Add at least one keyword, separated by commas."
    else:
        st.session_state.custom_categories.append(
            {"name": name, "icon": st.session_state.new_cat_icon, "keywords": keywords})
        resort_tasks()  # existing tasks that match move into the new category
        st.session_state.new_cat_name = ""
        st.session_state.new_cat_keywords = ""
        st.session_state.message = f'Created "{name}".'


# ---------- Header ----------
st.title("Daily Brain")
st.caption("Talk or type your to-dos. I'll sort them for you. "
           "Your list saves automatically on this device.")

# ---------- Brain dump ----------
st.text_area(
    "What's on your mind today?",
    key="brain_dump",
    height=120,
    placeholder="e.g. study for my exam, send the invoice to my client, and book a dentist appointment",
    help="On a phone, tap the 🎤 on your keyboard to talk instead of typing.",
)
st.button("Sort my tasks", type="primary", on_click=handle_brain_dump, width="stretch")
if st.session_state.get("message"):
    st.success(st.session_state.pop("message"))

# ---------- Task list, grouped by category ----------
tasks = st.session_state.tasks
if not tasks:
    st.info("Your list is empty. Add a few tasks above to get started.")

for category in all_categories():
    in_category = [t for t in tasks if t["category"] == category]
    if not in_category:
        continue
    st.markdown(f"#### {icon_for(category)} {category}")
    for t in in_category:
        # A horizontal row keeps the ⋯ menu beside the task, even on phones.
        with st.container(horizontal=True, vertical_alignment="center"):
            t["done"] = st.checkbox(t["task"], value=t["done"], key=f"done_{t['id']}",
                                    width="stretch")
            # The ⋯ menu lets people fix a wrong category or remove a task.
            with st.popover("⋯"):
                options = all_categories()
                # The key includes the current category, so the menu always
                # starts out showing where the task is right now.
                menu_key = f"cat_{t['id']}_{t['category']}"
                st.selectbox("Move to", options, index=options.index(t["category"]),
                             key=menu_key, on_change=move_task, args=(t["id"], menu_key))
                st.button("Delete", key=f"del_{t['id']}", on_click=delete_task,
                          args=(t["id"],))

if tasks:
    done_count = sum(t["done"] for t in tasks)
    st.caption(f"✅ {done_count} of {len(tasks)} done")
    if st.button("Clear completed", width="stretch"):
        st.session_state.tasks = [t for t in tasks if not t["done"]]
        st.rerun()

# ---------- Make it yours ----------
st.divider()
with st.expander("Create your own category", key="exp_categories", on_change="rerun"):
    st.caption("Tasks with these keywords will go into your category first.")
    st.text_input("Category name", key="new_cat_name", placeholder="e.g. Kids")
    st.selectbox("Icon", ICON_CHOICES, key="new_cat_icon")
    st.text_input("Keywords (separate with commas)", key="new_cat_keywords",
                  placeholder="e.g. soccer, daycare, pediatrician")
    st.button("Add category", on_click=handle_new_category)
    if st.session_state.get("cat_error"):
        st.error(st.session_state.pop("cat_error"))

    for c in st.session_state.custom_categories:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f"{c['icon']} **{c['name']}**: {', '.join(c['keywords'])}",
                        width="stretch")
            if st.button("Remove", key=f"rm_{c['name']}"):
                st.session_state.custom_categories = [
                    x for x in st.session_state.custom_categories if x["name"] != c["name"]]
                for t in tasks:
                    if t["category"] == c["name"]:
                        t["moved"] = False  # let these be sorted again
                resort_tasks()
                st.rerun()

with st.expander("Keep these together", key="exp_keep", on_change="rerun"):
    st.caption('Things that should never be split into separate tasks, one per line. '
               'For example: "lemon pepper and garlic blend" or "rice and beans".')
    keep_text = st.text_area("Keep together", value="\n".join(st.session_state.keep_together),
                             label_visibility="collapsed", height=100)
    st.session_state.keep_together = [p.strip() for p in keep_text.splitlines() if p.strip()]

with st.expander("Back up or move your list", key="exp_backup", on_change="rerun"):
    st.caption("Your list lives in this browser. Clearing your browser data erases it, "
               "so download a backup now and then, or use one to move your list to another device.")
    st.download_button(
        "Download a backup",
        data=json.dumps({k: st.session_state[k] for k in empty_state()}, indent=2),
        file_name=f"daily-brain-{date.today().isoformat()}.json",
        mime="application/json",
        width="stretch",
    )
    uploaded = st.file_uploader("Restore from a backup", type="json")
    if uploaded is not None and st.button("Restore it"):
        try:
            loaded = json.load(uploaded)
            if isinstance(loaded, list):  # older backups were just a list of tasks
                loaded = {"tasks": loaded}
            for t in loaded.get("tasks", []):
                t.setdefault("id", str(uuid.uuid4()))
                t.setdefault("done", False)
                t.setdefault("moved", False)
            state = empty_state()
            state.update(loaded)
            st.session_state.update(state)
            resort_tasks()
            st.rerun()
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            st.error("That file doesn't look like a Daily Brain backup.")

st.caption("🔒 Your tasks stay on your device. Nothing is stored on a server.")

save_to_browser()
