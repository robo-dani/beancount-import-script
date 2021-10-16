import enum

from decimal import Decimal
from datetime import datetime as dt

import beancount.core.data as bc_data
from beancount.core.amount import Amount
from beancount.core.position import Cost


from beancount.ingest import importer
from typing import Callable, Dict


class Col(enum.Enum):
    DATE = "Day"
    NARRATION = "Narration"
    CURRENCY = "Currency"
    ID = "Id"
    STOCK = "Stock"  # stock name
    PRICE = "price"
    NUMBER = "Number"  # 数量
    AMOUNT_POS = "actual amount"  # 总价 减去手续费
    AMOUNT_PRE = "trade amount"  # 未减手续费
    COMMISSION = "Commission"
    STAMP = "Stamp_duty"
    TRANS = "Transfer fee"
    OTHER = "Other fees"


class StockImporter(importer.ImporterProtocol):
    """Importer for files"""
    list_comm = [Col.STAMP, Col.TRANS, Col.OTHER, Col.COMMISSION]

    def __init__(self, currency: str, reader: Callable, account_cash: str, account_stock: str, account_comm: dict,
                 account_pnl: str, generate_commodity: bool =False):
        """
        :param currency: 货币单位
        :param reader: 读取文件函数
        :param account_cash: 现金扣款账户
        :param account_stock: 股票对应的虚拟账户
        :param account_comm: 一堆手续费的账户, 假如不想分就只填个commission的吧
        :param account_pnl: 盈亏
        :param generate_commodity: 是否为股票commodity 生成 metadata name(就是对应的中文名)
        """
        self.currency = currency
        self.reader = reader
        self.account_cash = account_cash
        self.account_stock = account_stock
        self.account_comm = account_comm
        self.account_pnl = account_pnl
        self.generate_commodity = generate_commodity
        self.flag = "*"

    # 用来检查该文件是否能import
    def identify(self, file):
        return "交割" in file.name

    # 读取文件并输出 trans 记录
    def extract(self, file, existing_entries=None):
        entries = []

        df = self.reader(file)

        if self.currency:
            df[Col.CURRENCY] = self.currency

        index = 0
        for index, row in df.iterrows():

            # trans 的meta, bean-extract 会根据 index 排序
            meta = bc_data.new_metadata(file.name, index)

            # self.flag = "*"
            currency = row[Col.CURRENCY]
            sign = 1
            if row[Col.AMOUNT_POS] > 0:
                sign = -1

            # 指令 directive/transaction
            # see beancount.core.data.transaction
            # meta, date, flag, payee, narration, tags, links, posting

            txn = bc_data.Transaction(meta, row[Col.DATE], self.flag, None, row[Col.NARRATION], bc_data.EMPTY_SET,
                                      bc_data.EMPTY_SET, [])

            # Attributes:
            # account, units, cost, price, flag, meta

            # cash part  金钱部分
            units = Amount(Decimal(row[Col.AMOUNT_POS]).quantize(Decimal(".01")), currency)
            txn.postings.append(
                bc_data.Posting(self.account_cash, units, None, None, None, None)
            )

            # 股票 stock part
            # 因为commodity 必须英文大小开头, 而且不允许中文, 就只能用数字替代了
            units = Amount(Decimal(round(sign * row[Col.NUMBER])), "CN." + str(row[Col.ID]))

            if sign == -1:
                # 卖出的情况 sell
                # costs 为空 {} beancount 根据账户的规则会自己推断
                costs = Cost(None, None, None, None)
                # 股票 stock
                price = Amount(Decimal(str(row[Col.PRICE])), currency)
                txn.postings.append(
                    bc_data.Posting(self.account_stock, units, costs, price, None, None)
                )
                # P/L
                # 让beancount 自己推断了
                txn.postings.append(
                    bc_data.Posting(self.account_pnl, None, None, None, None, None)
                )
            else:
                # buy
                # 单价位数不定, str算了
                costs = Cost(Decimal(str(row[Col.PRICE])), currency, None, None)
                txn.postings.append(
                    bc_data.Posting(self.account_stock, units, costs, None, None, None)
                )

            # 手续费 commission part
            # 因为华宝有四个栏目, 所以就分开记了, 假如懒得分的话, 就直接传一个commission就行了， 这样四个栏目都记为commission
            sum_comm = 0
            if self.account_comm:
                for i in self.list_comm:
                    if self.account_comm.get(i) is None:
                        sum_comm += row[i]
                        continue
                    money = row[i]
                    if i == Col.COMMISSION:
                        money += sum_comm
                    if money == 0:
                        continue
                    units = Amount(Decimal(money).quantize(Decimal(".01")), currency)
                    txn.postings.append(
                        bc_data.Posting(
                            self.account_comm.get(i), units, None, None, None, None
                        )
                    )
            entries.append(txn)

        if self.generate_commodity is True:
            # 生成commodity 注释 这样bean-query或者fava就能显示中文名了
            ddf = df.drop_duplicates(Col.ID)
            for ind, row in ddf.iterrows():
                meta = bc_data.new_metadata("commodity", ind + index + 1)
                meta["name"] = row[Col.STOCK]
                # Attributes:
                # meta: dict, date: datetime.date, currency:str
                txn = bc_data.Commodity(meta, dt.today().date(), "CN." + str(row[Col.ID]))
                entries.append(txn)
        return entries
