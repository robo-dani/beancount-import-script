import sys

sys.path.append("./.")

from Importer import Importer
from stock_importer import StockImporter
from stock_importer import Col as St_col

import izly_reader
import SG_reader
import hwabao_reader

# izly part
izly_nar_reg = {
    "Payment": "CROUS RU",
    "Top-up": "izly account Top-up"
}

izly_account_sub = {"CROUS RU": "Expenses:Food:RU",
                    "Top-up": "Assets:Bank:FR:SG:Card7317"
                    }

izly_importer = Importer("EUR", reader=izly_reader.read,
                         account_main="Assets:Ecash:FR:Izly",
                         time_format="%m/%d/%Y",
                         account_sub=izly_account_sub,
                         nar_reg=izly_nar_reg)

# SG part
SG_nar_reg = {r"CARTE X\d{4} [0-3]\d/[0-1]\d (.*) \d+IOPD": "\g<1>",
              r"(VRST GAB).*(\d{2}H\d{2}) \d+ ([A-Z]+).*CARTE X+\d+X": "[\g<1>] dépose en especes on \g<2> at \g<3>",
              r"NYA\*S2LR01": "洗衣, 烘干"
              }

SG_account_sub = {"AUCHAN": "Expenses:Shopping",
                  "洗衣|烘干": "Expenses:House:Laundry",
                  "ROBERVAL": "Expenses:House:Rent",
                  "BOUYGTEL": "Expenses:Personal:Telephone",
                  "dépose": "Assets:Cash:FR",
                  "BURGER": "Expenses:Food"
                  }

SG_importer = Importer("EUR", reader=SG_reader.read,
                       account_main="Assets:Bank:FR:SG:Card7317",
                       time_format="%d/%m/%Y",
                       account_sub=SG_account_sub,
                       nar_reg=SG_nar_reg)

# hwabao part
hwabao_account = {
    St_col.COMMISSION: "Expenses:Financial:Commissions",
    St_col.TRANS: "Expenses:Financial:TransferFee",
    St_col.STAMP: "Expenses:Financial:StampFee",
    St_col.OTHER: "Expenses:Financial:Other"
                  }

hwabao_importer = StockImporter("CNY", reader=hwabao_reader.read,
                                account_cash="Assets:Trade:HwaBao:Ecash",
                                account_stock="Assets:Trade:HwaBao:Stock",
                                account_comm=hwabao_account,
                                account_pnl="Income:Trade:PnL"
                                )

# 因为没有做文件检测, 所以手动选择..
CONFIG = [hwabao_importer]
