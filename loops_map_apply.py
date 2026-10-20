"""
loops_map_apply.py
------------------
for loops, map() and apply() with lambda: the same tasks solved each way,
with timings, to show when each one is the right choice.

The example: a loan book of 100,000 loans in a pandas DataFrame.

Run it:  python loops_map_apply.py

Parts:
    1. Lambda: a function without a name
    2. Plain Python lists: for loop, list comprehension, map()
    3. One pandas column: for loop, Series.apply(lambda), vectorised
    4. Several columns per row: iterrows, DataFrame.apply(axis=1), vectorised
    5. Lookups and conditions: Series.map(dict), apply(lambda), np.where / np.select
    6. When the for loop is the right tool
    7. Summary
"""

import time

import numpy as np
import pandas as pd

N_LOANS = 100_000
rng = np.random.default_rng(42)          # fixed seed: the same data at every run

loans = pd.DataFrame({
    "loan_id": np.arange(1, N_LOANS + 1),
    "amount": rng.integers(50_000, 500_000, N_LOANS).astype(float),
    "annual_rate": rng.uniform(0.02, 0.08, N_LOANS).round(4),
    "years": rng.choice([10, 15, 20, 25, 30], N_LOANS),
    "currency": rng.choice(["GBP", "EUR", "USD"], N_LOANS),
    "ltv": rng.uniform(0.40, 1.00, N_LOANS).round(3),   # loan-to-value ratio
})


def timed(label: str, func, repeat: int = 3):
    """Run func `repeat` times, print the best time, return (result, seconds)."""
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        result = func()
        best = min(best, time.perf_counter() - start)
    print(f"  {label:<44} {best * 1000:>9.1f} ms")
    return result, best


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# =============================================================================
# 1. LAMBDA: a function without a name
# =============================================================================
section("1. Lambda: a function without a name")

# These two lines define the same function:
def monthly_interest(amount, rate):
    return amount * rate / 12

monthly_interest_lambda = lambda amount, rate: amount * rate / 12   # noqa: E731

print("def    ->", monthly_interest(120_000, 0.05))
print("lambda ->", monthly_interest_lambda(120_000, 0.05))
print("""
A lambda is a one-line function written where it is used:
    lambda <arguments>: <expression>
- It can hold ONE expression only: no loops, no several statements.
- Use it for short functions passed to map(), apply(), sorted(key=...).
- If you give it a name (as above) or it grows complex, write a def instead.

A lambda is not a technique of its own: it is the function you give to
map() or apply(). The speed comes from map/apply, not from the lambda.""")


# =============================================================================
# 2. PLAIN PYTHON LISTS
# =============================================================================
section("2. Plain Python lists: monthly interest of each loan")
amounts = loans["amount"].tolist()
rates = loans["annual_rate"].tolist()

def with_for_loop():
    result = []                                   # start with an empty list
    for amount, rate in zip(amounts, rates):      # zip pairs the two lists
        result.append(amount * rate / 12)
    return result

def with_comprehension():
    # The same loop, written as one expression: [expression for item in items]
    return [amount * rate / 12 for amount, rate in zip(amounts, rates)]

def with_map_lambda():
    # map(function, list1, list2) calls the function on each pair of items.
    # It returns a lazy "map object": list() makes it produce the values.
    return list(map(lambda amount, rate: amount * rate / 12, amounts, rates))

def with_map_function():
    return list(map(monthly_interest, amounts, rates))   # a named function works too

r1, _ = timed("for loop + append", with_for_loop)
r2, _ = timed("list comprehension", with_comprehension)
r3, _ = timed("map(lambda ...)", with_map_lambda)
r4, _ = timed("map(named function)", with_map_function)
assert r1 == r2 == r3 == r4                       # same result every way
print("""  -> All four give identical results, at similar speeds: each one calls
     Python code once per item. The comprehension is the usual choice: it is
     the most readable. map() reads well with an existing named function:
     list(map(str.upper, names)).""")


# =============================================================================
# 3. ONE PANDAS COLUMN
# =============================================================================
section("3. One pandas column: amount in thousands")

def column_for_loop():
    values = []
    for amount in loans["amount"]:
        values.append(amount / 1_000)
    return pd.Series(values, index=loans.index)

def column_apply_lambda():
    # Series.apply calls the lambda once per value: a for loop, hidden.
    return loans["amount"].apply(lambda amount: amount / 1_000)

def column_vectorised():
    # Vectorised: ONE operation on the whole column. pandas hands it to NumPy,
    # which runs the loop in compiled C code instead of Python.
    return loans["amount"] / 1_000

a, t_loop = timed("for loop", column_for_loop)
b, t_apply = timed("Series.apply(lambda)", column_apply_lambda)
c, t_vec = timed("vectorised: loans['amount'] / 1_000", column_vectorised)
pd.testing.assert_series_equal(a, b, check_names=False)
pd.testing.assert_series_equal(b, c, check_names=False)
print(f"""  -> apply(lambda) takes about as long as the for loop: it IS a loop, hidden.
     Vectorised is about {t_apply / t_vec:,.0f} times faster than both.""")


# =============================================================================
# 4. SEVERAL COLUMNS PER ROW
# =============================================================================
section("4. Several columns per row: monthly payment of each loan")
# Payment = P x r / (1 - (1 + r)^-n), with r the monthly rate, n the months.

def payment(amount, annual_rate, years):
    r = annual_rate / 12
    n = years * 12
    return amount * r / (1 - (1 + r) ** -n)

def rows_iterrows():
    # iterrows() builds a new Series object for EVERY row: the slowest way.
    return pd.Series([payment(row["amount"], row["annual_rate"], row["years"])
                      for _, row in loans.iterrows()], index=loans.index)

def rows_itertuples():
    # itertuples() yields light tuples: much faster when a loop is needed.
    return pd.Series([payment(t.amount, t.annual_rate, t.years)
                      for t in loans.itertuples(index=False)], index=loans.index)

def rows_apply_lambda():
    # axis=1: call the lambda once per ROW; `row` holds that row's values.
    return loans.apply(lambda row: payment(row["amount"], row["annual_rate"], row["years"]),
                       axis=1)

def rows_vectorised():
    # The same formula, on whole columns at once: no loop in Python at all.
    return payment(loans["amount"], loans["annual_rate"], loans["years"])

timed_rows = {}
for label, func in [("iterrows()", rows_iterrows),
                    ("itertuples()", rows_itertuples),
                    ("DataFrame.apply(lambda row, axis=1)", rows_apply_lambda),
                    ("vectorised: payment(column, column, column)", rows_vectorised)]:
    timed_rows[label] = timed(label, func, repeat=1 if "iterrows" in label else 3)

results = [r for r, _ in timed_rows.values()]
for r in results[1:]:
    pd.testing.assert_series_equal(results[0], r, check_names=False)
fastest = timed_rows["vectorised: payment(column, column, column)"][1]
slowest = timed_rows["iterrows()"][1]
t_tuples = timed_rows["itertuples()"][1]
t_rowapply = timed_rows["DataFrame.apply(lambda row, axis=1)"][1]
print(f"  -> The same function, payment(), runs about {slowest / fastest:,.0f} times faster")
print("     on whole columns than row by row with iterrows(). It works because")
print("     it uses only arithmetic (+ - * / **), which pandas applies to columns.")
print(f"  -> When a row-by-row loop cannot be avoided, itertuples() is about "
      f"{t_rowapply / t_tuples:.1f} times")
print("     faster than apply(axis=1): apply builds a Series for every row, like iterrows.")


# =============================================================================
# 5. LOOKUPS AND CONDITIONS
# =============================================================================
section("5a. Lookups: currency code -> currency name")
names = {"GBP": "Pound sterling", "EUR": "Euro", "USD": "US dollar"}

m1, t_apply = timed("Series.apply(lambda c: names[c])",
                    lambda: loans["currency"].apply(lambda c: names[c]))
m2, t_map = timed("Series.map(names)", lambda: loans["currency"].map(names))
pd.testing.assert_series_equal(m1, m2)
print(f"""  -> Series.map(dictionary) is the tool for lookups: about {t_apply / t_map:.1f} times
     faster here, and shorter. A code missing from the dictionary becomes NaN,
     which is easy to detect with .isna().""")

section("5b. Conditions: risk band from the loan-to-value ratio")
# Rule: LTV above 90% = high, above 75% = medium, otherwise low.

def band(ltv):
    if ltv > 0.90:
        return "high"
    if ltv > 0.75:
        return "medium"
    return "low"

def bands_apply():
    return loans["ltv"].apply(band)

def bands_select():
    # np.select checks the conditions in order, on the whole column at once,
    # and takes the first that is true: the vectorised form of if / elif / else.
    conditions = [loans["ltv"] > 0.90, loans["ltv"] > 0.75]
    return pd.Series(np.select(conditions, ["high", "medium"], default="low"),
                     index=loans.index)

def bands_cut():
    # pd.cut is made for bands: value ranges -> labels.
    return pd.cut(loans["ltv"], bins=[0, 0.75, 0.90, 1.0],
                  labels=["low", "medium", "high"]).astype(str)

print("  Text results (risk band):")
s1, t_apply = timed("Series.apply(band)  (if / elif / else)", bands_apply)
s2, t_select = timed("np.select(conditions, choices)", bands_select)
s3, t_cut = timed("pd.cut(bins, labels)", bands_cut)
assert (s1 == s2).all() and (s1 == s3).all()

# The same rule with NUMBERS as results: a capital weight per band.
def weight(ltv):
    if ltv > 0.90:
        return 1.00
    if ltv > 0.75:
        return 0.50
    return 0.35

print("  Number results (capital weight):")
w1, t_apply_num = timed("Series.apply(weight)", lambda: loans["ltv"].apply(weight))
w2, t_select_num = timed("np.select(conditions, choices)", lambda: pd.Series(
    np.select([loans["ltv"] > 0.90, loans["ltv"] > 0.75], [1.00, 0.50], default=0.35),
    index=loans.index))
pd.testing.assert_series_equal(w1, w2, check_names=False)
print(f"""  -> np.select is {t_apply / t_select:.1f} times faster than apply with text results,
     {t_apply_num / t_select_num:.0f} times faster with numbers. Text gains less: Python must still
     create a string object for every row. pd.cut, made for bands, is {t_apply / t_cut:.1f} times
     faster than apply. For two outcomes: np.where(condition, if_true, if_false).""")


# =============================================================================
# 6. WHEN THE FOR LOOP IS THE RIGHT TOOL
# =============================================================================
section("6. When the for loop is the right tool")

# 6a. Each step depends on the previous one: an amortisation schedule.
# This month's interest depends on LAST month's balance, so the months cannot
# be computed all at once.
amount, rate, years = 200_000, 0.045, 25
monthly = payment(amount, rate, years)
balance = amount
schedule = []
for month in range(1, years * 12 + 1):
    interest = balance * rate / 12
    balance -= monthly - interest
    schedule.append((month, round(interest, 2), round(balance, 2)))
print(f"6a. Sequential calculation: {len(schedule)} months, "
      f"first interest {schedule[0][1]:,.2f}, final balance {abs(schedule[-1][2]):,.2f}")

# 6b. Stopping early: `break` ends the loop as soon as the answer is known.
# map() and apply() always process every item.
for month, interest, bal in schedule:
    if bal < amount / 2:
        print(f"6b. Early exit: half the loan is repaid after {month} months "
              f"({month / 12:.1f} years); the loop stopped there")
        break

# 6c. Actions rather than values: writing files, calling an API, sending
# messages. A loop states plainly that something is DONE for each item.
by_currency = {cur: group for cur, group in loans.groupby("currency")}
for cur, group in by_currency.items():
    # group.to_csv(f"loans_{cur}.csv", index=False)   # one file per currency
    print(f"6c. Side effect per group: would write loans_{cur}.csv ({len(group):,} rows)")


# =============================================================================
# 7. SUMMARY
# =============================================================================
section("7. Summary: which one to use")
print("""
  Task                                         Best choice
  -------------------------------------------  ----------------------------------
  Arithmetic on pandas columns                 vectorised: df["a"] * df["b"]
  if / elif / else on a column                 np.where, np.select or pd.cut
  Replace codes with labels (lookup)           Series.map(dictionary)
  Text operations on a column                  .str methods: df["c"].str.upper()
  Logic with no vectorised form                Series.apply(function)
  A function needing several columns per row   vectorise it (part 4)
  Row-by-row loop, if it cannot be vectorised  itertuples(): faster than apply(axis=1)
  Short row-wise code, speed not critical      df.apply(lambda row: ..., axis=1)
  Transform a Python list                      list comprehension
  Apply an existing function to a list         map(function, list)
  Each step depends on the previous one        for loop
  Stop as soon as a condition is met           for loop + break
  Actions per item (files, API calls)          for loop

  On one column:    vectorised  >  map(dict)  >  apply  ~  for loop
  Row by row:       vectorised  >  itertuples  >  apply(axis=1)  >  iterrows
  On Python lists:  comprehension  ~  map  ~  for loop: choose the most readable
""")
