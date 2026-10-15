"""Oman business calendar used by the reporting date dimension and the demo seed data.

Islamic dates are the expected (astronomical) dates for Oman; the official dates may shift by a day.
"""
import datetime

D = datetime.date

RAMADAN = {
    2024: (D(2024, 3, 11), D(2024, 4, 9)),
    2025: (D(2025, 3, 1), D(2025, 3, 30)),
    2026: (D(2026, 2, 18), D(2026, 3, 19)),
    2027: (D(2027, 2, 8), D(2027, 3, 9)),
}
EID_AL_FITR = {2024: D(2024, 4, 10), 2025: D(2025, 3, 31), 2026: D(2026, 3, 20), 2027: D(2027, 3, 10)}
EID_AL_ADHA = {2024: D(2024, 6, 16), 2025: D(2025, 6, 6), 2026: D(2026, 5, 27), 2027: D(2027, 5, 16)}
# Khareef (monsoon) tourist season in Dhofar / Salalah.
KHAREEF = {year: (D(year, 6, 21), D(year, 9, 21)) for year in range(2024, 2028)}

WEEKEND_WEEKDAYS = {4, 5}  # Friday, Saturday (Python weekday numbers)


def is_ramadan(day):
    span = RAMADAN.get(day.year)
    return bool(span and span[0] <= day <= span[1])


def is_eid(day):
    """Eid holidays: 3 days of Eid al-Fitr and 4 days of Eid al-Adha."""
    fitr, adha = EID_AL_FITR.get(day.year), EID_AL_ADHA.get(day.year)
    return bool((fitr and 0 <= (day - fitr).days <= 2) or (adha and 0 <= (day - adha).days <= 3))


def is_pre_eid(day, days=10):
    """The shopping peak in the run-up to each Eid."""
    for table in (EID_AL_FITR, EID_AL_ADHA):
        eid = table.get(day.year)
        if eid and 0 < (eid - day).days <= days:
            return True
    return False


def is_khareef(day):
    span = KHAREEF.get(day.year)
    return bool(span and span[0] <= day <= span[1])


def is_weekend(day):
    return day.weekday() in WEEKEND_WEEKDAYS


def ramadan_sql_condition(column="d"):
    """SQL boolean expression: is the date column inside Ramadan?"""
    parts = [f"({column} BETWEEN DATE '{s}' AND DATE '{e}')" for s, e in RAMADAN.values()]
    return "(" + " OR ".join(parts) + ")"


def eid_sql_condition(column="d"):
    parts = [f"({column} BETWEEN DATE '{d}' AND DATE '{d + datetime.timedelta(days=2)}')" for d in EID_AL_FITR.values()]
    parts += [f"({column} BETWEEN DATE '{d}' AND DATE '{d + datetime.timedelta(days=3)}')" for d in EID_AL_ADHA.values()]
    return "(" + " OR ".join(parts) + ")"
