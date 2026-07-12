"""Prompt enrichment: a neutral desktop preamble + optional per-app context +
battle-tested task presets.

Every task the fleet runs is app-agnostic — the same worker desktop can host
Tryton, Thunderbird, LibreOffice, a browser, etc. So the base preamble stays
app-neutral, and any app-specific guidance (like the Tryton UI hints validated
in M0-M2 runs — the Attachments-dialog anatomy and the two-"+"-buttons
distinction) lives in a per-app CONTEXT block attached only to that app's tasks.
"""

from __future__ import annotations

# App-neutral: how to operate ANY desktop app by looking + clicking + typing.
BASE_PREAMBLE = (
    "You are controlling a Linux desktop (X11) by looking at the screen and using the "
    "mouse and keyboard, exactly like a human would. Applications open in windows on the "
    "desktop. Work step by step: take a screenshot to see the current state, then act, "
    "then look again. General tips: application menus are along the top of each window; a "
    "file-open/save dialog accepts a typed path via Ctrl+L; save with Ctrl+S. If a dialog "
    "blocks you, read it and respond before continuing.\n\n"
)

# How to finish — this is what lets retrieval/summarization tasks surface their
# result. The agent's final answer is shown to the user in the UI (the green
# "Answer" box), so a report-style task must put the requested info THERE.
ANSWER_GUIDANCE = (
    "Finishing the task: if it asks you to FIND, READ, LOOK UP, RETRIEVE, SUMMARIZE, "
    "COUNT, or otherwise REPORT information (e.g. \"summarize my unread emails\", \"what's "
    "the total in column B\", \"how many messages are from Pam\"), your final answer MUST "
    "BE that information itself, written out clearly for the user — that answer is what "
    "they see. If the task is purely an ACTION with nothing to report back (e.g. \"create "
    "a sale\", \"attach a file\", \"save the document\"), reply with the single word: done.\n\n"
)

# App-specific context. Attached to a task only when it targets that app, so a
# Thunderbird or free-text task never gets Tryton's ERP hints stapled on.
TRYTON_CONTEXT = (
    "App context — you are in the Tryton ERP desktop client (GTK), logged in as admin, "
    "company Dunder Mifflin. The main menu tree is on the left (Parties, Companies, "
    "Products, Sales, ...). A group header only expands/collapses; the item with the list "
    "icon below it opens the data view (double-click it). There are TWO different \"+\" "
    "buttons: the top-toolbar \"+\" creates a new top-level record; the small \"+\" at the "
    "right end of a sub-list bar (like \"Lines\") adds a child row. Records get their "
    "Number only after saving. To identify a record in a list, use the State column "
    "(drafts show an empty Number cell). If a save fails, a dialog names the missing "
    "required field.\n\n"
)

# Preset tasks. Keys are stable API identifiers. A preset may carry an optional
# "context" (app-specific block prepended for that task); the Tryton ones do.
PRESETS: dict[str, dict[str, str]] = {
    "create_sale": {
        "label": "Create & quote a sale (Office Chair x4)",
        "context": TRYTON_CONTEXT,
        "task": (
            "Create and confirm a sales order.\n"
            '1. Expand "Sales" in the left menu and double-click the "Sales" list item.\n'
            '2. Click the top-toolbar "+" (New). A blank sale form opens (State: Draft).\n'
            '3. Click the "Party" field (this IS the customer field). Type: Pam Beesly — '
            "select it from the dropdown. Addresses auto-fill.\n"
            '4. Set "Sale Date" to today. Skipping it makes the save fail.\n'
            '5. In the "Lines" section, click the "+" at the right end of the Lines bar '
            "(NOT the top-toolbar one). It only works after Party is set.\n"
            "6. In the new row: Product -> Office Chair, Quantity -> 4.\n"
            "7. Save with Ctrl+S. A Number appears and Total is non-zero.\n"
            '8. Click the "Quote" button bottom-right. State becomes Quotation.\n'
            "9. Answer with the word: done."
        ),
    },
    "create_customer": {
        "label": "Create a customer with contact",
        "context": TRYTON_CONTEXT,
        "task": (
            "Create a new customer.\n"
            '1. Expand "Parties" in the left menu and double-click the "Parties" list item.\n'
            '2. Click the top-toolbar "+" (New).\n'
            "3. Name: Stamford Paper Co\n"
            '4. In the "Contact Mechanisms" sub-list bar, click the "open/edit record" icon '
            '(the square with an arrow, next to the "+") to add the contact via ITS FORM '
            "DIALOG — do NOT type into the inline grid cells (the Value cell corrupts "
            "typed text). In the dialog set Type: E-Mail and Value: "
            "orders@stamfordpaper.com then confirm with OK/Add.\n"
            "5. Save with Ctrl+S.\n"
            "6. Answer with the word: done."
        ),
    },
    "create_product": {
        "label": "Create salable product (Desk Lamp)",
        "context": TRYTON_CONTEXT,
        "task": (
            "Create a new salable product.\n"
            '1. Expand "Products" in the left menu and double-click the "Products" list item.\n'
            '2. Click the top-toolbar "+" (New).\n'
            "3. Name: Desk Lamp\n"
            "4. Type: Goods. Default UOM: Unit.\n"
            "5. List Price: 35.00\n"
            '6. Tick the "Salable" checkbox (a Sale tab appears; leave Sale UOM = Unit).\n'
            "7. Save with Ctrl+S.\n"
            "8. Answer with the word: done."
        ),
    },
    "attach_document": {
        "label": "Attach contract to Acme sale",
        "context": TRYTON_CONTEXT,
        "task": (
            "Attach the file /mnt/docs/acme_contract.txt to the Acme Corp sale whose State "
            "column reads Processing.\n"
            '1. Expand "Sales" and double-click the "Sales" list item.\n'
            "2. There are TWO Acme Corp sales. Double-click the one whose State is "
            "Processing (NOT the Draft one).\n"
            "3. Click the paperclip (Attachments) icon in the top toolbar. The Attachments "
            "window is a grid with columns Name, Data, Link.\n"
            '4. Click the "+" icon in that window once — one new empty row appears.\n'
            "5. Do NOT type into the Name column. Click the small file-selector icon inside "
            "the Data column of the new row. A GTK file chooser opens.\n"
            "6. Press Ctrl+L, type exactly /mnt/docs/acme_contract.txt and press Enter. Do "
            "NOT select internal_notes.txt (a decoy).\n"
            "7. The row's Name should now read acme_contract.txt. If not, correct it.\n"
            "8. Click Close. Answer with the word: done."
        ),
    },
}


def build_prompt(text: str, preset: str | None) -> str:
    """Assemble the full message sent to the agent:

        BASE_PREAMBLE  (app-neutral desktop operation)
      + <app context>  (only if the preset declares one)
      + ANSWER_GUIDANCE (report info vs. reply "done")
      + Task: <preset body or the user's free text>

    Free-text tasks get no app context (we don't know which app they target),
    so they're never mis-primed with, say, Tryton's ERP hints.
    """
    if preset and preset in PRESETS:
        context = PRESETS[preset].get("context", "")
        body = PRESETS[preset]["task"]
    else:
        context = ""
        body = text
    return f"{BASE_PREAMBLE}{context}{ANSWER_GUIDANCE}Task: {body}"
