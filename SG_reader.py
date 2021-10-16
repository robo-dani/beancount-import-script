import re
import pandas as pd
import datetime
from decimal import Decimal
import csv

from io import StringIO
from Importer import Col

COL_MAP = {"Date de l'opération": Col.DATE,
           "Détail de l'écriture": Col.NARRATION,
           "Montant de l'opération": Col.MONEY}

date_pat = re.compile("[0-3][0-9]/[0-1][0-9]")


def date_replace(row):
    jour = date_pat.findall(row[Col.NARRATION])
    if jour:
        row[Col.DATE] = jour[0] + "/2021"


def read(file) -> pd.DataFrame:
    csv_data = file.contents()
    return read_adp(csv_data)


def read_adp(csv_data) -> pd.DataFrame:
    start_pos = csv_data.find("Date")
    csv_data = csv_data[start_pos:]
    df = pd.read_csv(StringIO(csv_data), delimiter=";")

    df.drop("Libellé", axis=1, inplace=True)
    df.rename(columns=COL_MAP, inplace=True)
    df.apply(date_replace, axis=1)

    return df


if __name__ == "__main__":
    with open("test/00050063461.csv", "r", encoding="Windows 1252") as f:
        data = f.read()
    print(read_adp(data))
