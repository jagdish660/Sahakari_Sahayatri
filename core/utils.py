# core/utils.py

def gregorian_to_nepali_approx(g_date):
    year = g_date.year + 57
    month = g_date.month
    day = g_date.day

    if month == 1:
        n_month = 9 if day < 14 else 10
    elif month == 2:
        n_month = 10 if day < 13 else 11
    elif month == 3:
        n_month = 11 if day < 14 else 12
    elif month == 4:
        n_month = 12 if day < 13 else 1
        if n_month == 1:
            year += 1
    elif month == 5:
        n_month = 1 if day < 14 else 2
    elif month == 6:
        n_month = 2 if day < 14 else 3
    elif month == 7:
        n_month = 3 if day < 16 else 4
    elif month == 8:
        n_month = 4 if day < 17 else 5
    elif month == 9:
        n_month = 5 if day < 17 else 6
    elif month == 10:
        n_month = 6 if day < 17 else 7
    elif month == 11:
        n_month = 7 if day < 16 else 8
    elif month == 12:
        n_month = 8 if day < 15 else 9
    else:
        n_month = 1

    return (year, n_month)
