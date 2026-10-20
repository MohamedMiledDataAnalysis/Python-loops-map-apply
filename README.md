# for loops, map() and apply(): when to use each

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)

One Python script that solves the same tasks with `for` loops, `map()`,
`apply()` with `lambda`, and vectorised pandas operations. It checks that
every method gives the same result, times each one, and shows when each
is the right choice.

The example data: a loan book of 100,000 loans in a pandas DataFrame.

```bash
pip install -r requirements.txt
python loops_map_apply.py
```

The script takes a few seconds; most of it is `iterrows()`, the slowest
method, which is the point of part 4.

---

## The short answer

| Task | Best choice |
|---|---|
| Arithmetic on pandas columns | vectorised: `df["a"] * df["b"]` |
| `if` / `elif` / `else` on a column | `np.where`, `np.select` or `pd.cut` |
| Replace codes with labels (lookup) | `Series.map(dictionary)` |
| Text operations on a column | `.str` methods: `df["c"].str.upper()` |
| Logic with no vectorised form | `Series.apply(function)` |
| A function needing several columns per row | vectorise it |
| Row-by-row loop, if it cannot be vectorised | `itertuples()` |
| Short row-wise code, speed not critical | `df.apply(lambda row: ..., axis=1)` |
| Transform a Python list | list comprehension |
| Apply an existing function to a list | `map(function, list)` |
| Each step depends on the previous one | `for` loop |
| Stop as soon as a condition is met | `for` loop + `break` |
| Actions per item (files, API calls) | `for` loop |

---

## The four tools

### `for` loop

Repeats a block of code once for each item.

```python
result = []
for amount, rate in zip(amounts, rates):
    result.append(amount * rate / 12)
```

`zip(amounts, rates)` pairs the two lists item by item.

### `lambda`

A function without a name, written where it is used.

```python
def monthly_interest(amount, rate):        # a named function
    return amount * rate / 12

lambda amount, rate: amount * rate / 12    # the same, as a lambda
```

- Syntax: `lambda <arguments>: <expression>`.
- It holds **one expression** only: no loops, no several statements.
- It is meant to be passed to another function: `map()`, `apply()`,
  `sorted(key=...)`.
- If a lambda needs a name, or grows complex, write a `def` instead.

A lambda is not a technique of its own: it is the function given to
`map()` or `apply()`. The speed comes from `map` or `apply`, not from the
lambda.

### `map()`

Two different `map`s exist:

| | Python `map()` | pandas `Series.map()` |
|---|---|---|
| Works on | any list | a pandas column |
| Takes | a function | a function **or a dictionary** |
| Example | `list(map(str.upper, names))` | `df["ccy"].map({"GBP": "Pound"})` |
| Returns | a lazy map object: wrap in `list()` | a Series |

### `apply()`

Calls a function on each element of a pandas object.

```python
df["amount"].apply(lambda a: a / 1_000)            # each VALUE of a column
df.apply(lambda row: row["a"] * row["b"], axis=1)  # each ROW of a DataFrame
```

`axis=1` means "one call per row"; `row` then holds that row's values,
accessed by column name.

### Vectorised operations: the reference

```python
df["amount"] / 1_000
```

One operation on the whole column. pandas hands it to NumPy, which runs
the loop in compiled C code instead of Python. No `for`, `map` or `apply`
appears, which is why it is so much faster.

---

## The results

Timings from one run on 100,000 loans. They vary by machine and run;
the **ratios** between methods are what matter.

### Part 2: Python lists (monthly interest)

| Method | Time |
|---|---|
| `for` loop + `append` | 4.9 ms |
| list comprehension | 3.7 ms |
| `map(lambda ...)` | 6.5 ms |
| `map(named function)` | 5.6 ms |

All four are in the same range: each calls Python code once per item.
**Choose the most readable.** The list comprehension usually is:

```python
[amount * rate / 12 for amount, rate in zip(amounts, rates)]
```

`map()` reads well with an existing named function:
`list(map(str.upper, names))`.

### Part 3: one pandas column (amount in thousands)

| Method | Time |
|---|---|
| `for` loop | 9.3 ms |
| `Series.apply(lambda)` | 11.4 ms |
| vectorised: `loans["amount"] / 1_000` | 0.1 ms |

`apply()` takes as long as the `for` loop: **it is a loop, hidden**.
Vectorised is about 100 times faster than both.

### Part 4: several columns per row (monthly payment)

The payment formula uses three columns:

```python
def payment(amount, annual_rate, years):
    r = annual_rate / 12
    n = years * 12
    return amount * r / (1 - (1 + r) ** -n)
```

| Method | Time |
|---|---|
| `iterrows()` | 2,071 ms |
| `DataFrame.apply(lambda row, axis=1)` | 498 ms |
| `itertuples()` | 134 ms |
| vectorised: `payment(df["amount"], df["annual_rate"], df["years"])` | 2.1 ms |

- The same function, `payment()`, runs about 1,000 times faster on whole
  columns than row by row with `iterrows()`.
- It can take whole columns because it uses only arithmetic
  (`+ - * / **`), which pandas applies to columns element by element.
  **Many functions written for one value already work on columns**:
  try them before writing a loop.
- When a row-by-row loop cannot be avoided, `itertuples()` is several
  times faster than `apply(axis=1)`. Both `iterrows()` and
  `apply(axis=1)` build a new Series object for every row;
  `itertuples()` yields light tuples.

### Part 5a: lookups (currency code → name)

| Method | Time |
|---|---|
| `Series.apply(lambda c: names[c])` | 11.8 ms |
| `Series.map(names)` | 6.2 ms |

`Series.map(dictionary)` is faster and shorter. A code missing from the
dictionary becomes `NaN`, easy to find with `.isna()`, where the
`apply` version would stop with a `KeyError`.

### Part 5b: conditions (risk band from the loan-to-value ratio)

The rule: above 90% is high risk, above 75% medium, otherwise low.

```python
def band(ltv):                          # for apply(): one value at a time
    if ltv > 0.90:
        return "high"
    if ltv > 0.75:
        return "medium"
    return "low"

np.select([df["ltv"] > 0.90, df["ltv"] > 0.75],   # vectorised
          ["high", "medium"], default="low")

pd.cut(df["ltv"], bins=[0, 0.75, 0.90, 1.0],      # made for bands
       labels=["low", "medium", "high"])
```

| Method | Text results | Number results |
|---|---|---|
| `Series.apply(function)` | 10.8 ms | 11.9 ms |
| `np.select(conditions, choices)` | 6.8 ms | 1.3 ms |
| `pd.cut(bins, labels)` | 2.6 ms | — |

- `np.select` checks the conditions in order and takes the first that is
  true: the vectorised form of `if` / `elif` / `else`.
- With **numbers** as results, `np.select` is about 9 times faster than
  `apply`. With **text**, the gain is smaller: Python must still create
  a string object for every row, whichever method chooses it.
- `pd.cut` is made for value bands and is the fastest here.
- For two outcomes, `np.where(condition, if_true, if_false)`.

---

## When the `for` loop is the right tool

Vectorised operations are fastest, but three situations call for a loop.
Part 6 of the script shows each one.

### 1. Each step depends on the previous one

An amortisation schedule: this month's interest depends on last month's
balance, so the months cannot be computed all at once.

```python
balance = amount
for month in range(1, years * 12 + 1):
    interest = balance * rate / 12
    balance -= monthly - interest
```

### 2. Stopping early

`break` ends the loop as soon as the answer is known; `map()` and
`apply()` always process every item.

```python
for month, interest, bal in schedule:
    if bal < amount / 2:
        print(f"Half repaid after {month} months")
        break
```

### 3. Actions rather than values

Writing one file per group, calling an API, sending messages: a loop
states plainly that something is **done** for each item.

```python
for currency, group in loans.groupby("currency"):
    group.to_csv(f"loans_{currency}.csv", index=False)
```

---

## Order of preference

```
On one column:    vectorised  >  map(dict)  >  apply  ~  for loop
Row by row:       vectorised  >  itertuples  >  apply(axis=1)  >  iterrows
On Python lists:  comprehension  ~  map  ~  for loop: the most readable
```

When `apply()` is still the right choice: the logic has no vectorised
form (calling an external library on each value, parsing irregular
text), the data is small, and readability matters more than speed.

---

## Comparison with R

| Python | R |
|---|---|
| `for` loop | `for` loop |
| list comprehension, `map()` | `lapply()`, `sapply()`, `purrr::map()` |
| `lambda x: x * 2` | `function(x) x * 2`, or `\(x) x * 2` (R 4.1+) |
| `Series.apply(f)` | `sapply(df$col, f)` |
| `df.apply(f, axis=1)` | `apply(df, 1, f)` |
| vectorised `df["a"] * 2` | vectorised `df$a * 2` |
| `np.where(cond, a, b)` | `ifelse(cond, a, b)` |
| `np.select(...)` | `dplyr::case_when(...)` |
| `pd.cut(...)` | `cut(...)` |
| `Series.map(dict)` | `unname(lookup[df$code])` with a named vector |

The lesson is the same in both languages: vectorised code first, loops
when each step depends on the previous one.

---

## Project structure

```
loops-map-apply/
├── loops_map_apply.py   the script: parts 1 to 7
├── requirements.txt     pandas, numpy
├── LICENSE
└── README.md
```

## Licence

MIT
