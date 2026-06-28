---
name: cc-statement
description: Use when parsing an Axis Bank credit card PDF statement to extract, group and categorise transactions, explore and transform the expense table, and optionally export to CSV.
---

# CC Statement Parser — Axis Bank

Parse a password-protected Axis Bank CC PDF into a grouped, categorised expense table. A shared knowledge file (`vendor_categories.json`) grows richer with each run — known vendors are auto-classified, unknowns are resolved interactively before the table is shown.

## Files (all in this skill's directory)

```
D:\projects\repos\claude-marketplace\plugins\personal\skills\cc-statement\
  extract.py              ← PDF → raw JSON transactions
  vendor_categories.json  ← growing vendor→category map (read + update each run)
```

Requires `pypdf`: `pip install pypdf`

---

## Step 1 — Inputs

Ask the user for:
- PDF path
- Password (**always prompt — never assume or default**)

---

## Step 2 — Extract

```
python "D:\projects\repos\claude-marketplace\plugins\personal\skills\cc-statement\extract.py" "<pdf_path>" "<password>"
```

Output: `{transactions: [{date, description, amount, type}], pages, total_transactions}`

If the output contains `"error"`, report it and stop.

---

## Step 3 — Load knowledge base

Read `vendor_categories.json`. It contains:
- `vendors`: canonical name → `{patterns[], category, notes?}`
- `exclusions`: lowercase substrings — skip any transaction whose lowercased description contains one
- `categories`: the 9 category labels

---

## Step 4 — Group & match

For each raw transaction:

1. **Skip** if description (lowercased) contains any exclusion substring.
2. **Credits** = merchant refunds only if not "payment received" / "cashback" / "rebate". Net refunds against the matched vendor's total (credits are negative amounts).
3. **Match** description (lowercased) against each vendor's `patterns` (substring). First match wins → assign canonical name + category.
4. **Unmatched** → hold in an unknowns list.

Accumulate per canonical name: sum amounts, track earliest–latest date.

---

## Step 5 — Resolve unknowns via AskUserQuestion (BEFORE showing the table)

If there are any unmatched transactions, **do not show the table yet**.

Batch them into groups of up to 4 and use the `AskUserQuestion` tool for each batch. For each unknown vendor:

- **Question**: `"What category is [VENDOR NAME] (₹X,XXX)?"` — include the total so the user has context
- **Options**: 3–4 most plausible categories for this vendor (infer from the name), listed in order of likelihood. The tool appends an "Other" option automatically for free-text input.
- **header**: short vendor name (≤12 chars)

Example — if the vendor is "SOMESH SANDEEP,Bangalore ₹2,189":

```
options: [
  { label: "Activities", description: "Personal service, grooming, wellness" },
  { label: "Food/Home Stuff", description: "Home service, plumber, electrician" },
  { label: "Shopping", description: "Retail purchase" },
  { label: "Other", description: "Doesn't fit a specific category" }
]
```

After the user answers each batch, proceed to the next batch. Once all unknowns have a category, continue to Step 6.

---

## Step 6 — Present the complete table

Now generate the fully-classified table — no `?` rows:

```
#    Date                  Description                           Amount (₹)    Category
---  --------------------  ------------------------------------  ------------  --------------------
1    20 May–13 Jun '26     Zepto                                    4,728.00   Food/Home Stuff
2    19 May–15 Jun '26     Blinkit                                  3,240.00   Food/Home Stuff
...
```

Follow with a **category subtotal block**.

---

## Step 7 — Interactive mode

**Stay in this mode until the user asks to export or ends the conversation.**

Respond naturally to any table transformation:

- **Reclassify**: change a row's category
- **Split**: break one grouped row into two
- **Merge**: combine two rows into one
- **Rename**: change a description label
- **Add/remove**: manual row or delete
- **Filter/subtotal**: show only a category
- **Any other calculation or view**

Keep the in-context table state current after every change.

---

## Step 8 — Create CSV

Only when the user explicitly asks ("create csv", "export", "save as csv", etc.):

1. Default path: same folder as the PDF, named `expenses_<MonYYYY>.csv`
2. Write with header: `Date,Description,Expense,Category`
3. Confirm the path written

---

## Step 9 — Persist new learnings

After the session, write back to `vendor_categories.json`:

**For each vendor the user classified:**
- Add a new entry (or update existing) with the raw description patterns observed
- Set the `category` field
- Add a meaningful `notes` field: describe what kind of business/service this is in one sentence — use the vendor name, location, and any context clues from how the user categorised it. This is what makes the knowledge base useful for future runs.

Example of a good notes value: `"Medical imaging clinic, Kolkata"` or `"Quick-service restaurant chain, Gurgaon"`.

**Also update** any entry where the user reclassified an already-known vendor.

---

## Category reference

| # | Label |
|---|---|
| 1 | Food/Home Stuff |
| 2 | Dining and Alcohol |
| 3 | Flights/Stay/Travel |
| 4 | Activities |
| 5 | Shopping |
| 6 | Other |
| 7 | EMI |
| 8 | Subscriptions |
| 9 | Surplus Investment |
