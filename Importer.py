import enum
import re

from datetime import datetime as dt
from decimal import Decimal
import beancount.core.data as bc_data
from beancount.core.amount import Amount
from beancount.ingest import importer
from typing import Callable, Dict


class Col(enum.Enum):
    DATE = "Day"
    MONEY = "Money"
    NARRATION = "Narration"
    CURRENCY = "Currency"


class Importer(importer.ImporterProtocol):
    """Importer for files"""

    def __init__(self, currency: str, reader: Callable, account_main: str , time_format: str, account_sub: Dict = {},
                 nar_reg: Dict = {}):
        """
        :param currency: 货币单位
        :param reader: 读取文件函数
        :param account_main: 主要账户
        :param account_sub: 其他账户 dict key 是正则匹配式, value是对应账户
        :param time_format: str to date.time 格式
        :param account_sub: dict narration的正则表达式和对应的 account
        :param nar_reg: dict narration美化, 正则匹配然后替换的表达式
        """
        self.currency = currency
        self.reader = reader
        self.account_main = account_main
        self.account_sub = account_sub
        self.time_format = time_format
        self.nar_reg = nar_reg
        self.flag = "*"

    # 用来检查该文件是否能import
    def identify(self, file):
        print(file.name)
        return True

    # 读取文件并输出 trans 记录
    def extract(self, file, existing_entries=None):
        entries = []

        df = self.reader(file)
        df_class = {col: df[col][0].__class__ for col in df}
        if df_class[Col.DATE] == str:
            df[Col.DATE] = df[Col.DATE].apply(lambda x: dt.strptime(x, self.time_format).date())
        if df_class[Col.MONEY] == str:
            df[Col.MONEY] = df[Col.MONEY].apply(lambda x: Decimal(x.replace(",", ".")))
        if not df_class.get(Col.CURRENCY):
            df[Col.CURRENCY] = self.currency

        for index, row in df.iterrows():
            meta = bc_data.new_metadata(file.name, index)

            self.flag = "*"

            date = row[Col.DATE]
            money = row[Col.MONEY]
            currency = row[Col.CURRENCY]
            narration = self.narration_beautify(row[Col.NARRATION])
            account_sub = self.account_sniffer(narration)

            # see beancount.core.data.transaction
            # Attributes:
            #   meta: See above.
            #   date: See above.
            #   flag: A single-character string or None. This user-specified string
            #     represents some custom/user-defined state of the transaction. You can use
            #     this for various purposes. Otherwise common, pre-defined flags are defined
            #     under beancount.core.flags, to flags transactions that are automatically
            #     generated.
            #   payee: A free-form string that identifies the payee, or None, if absent.
            #   narration: A free-form string that provides a description for the transaction.
            #     All transactions have at least a narration string, this is never None.
            #   tags: A set of tag strings (without the '#'), or EMPTY_SET.
            #   links: A set of link strings (without the '^'), or EMPTY_SET.
            #   postings: A list of Posting instances, the legs of this transaction. See the
            #     doc under Posting above.
            txn = bc_data.Transaction(meta, date, self.flag, None, narration, bc_data.EMPTY_SET, bc_data.EMPTY_SET, [])
            units = Amount(money, currency)

            txn.postings.append(
                bc_data.Posting(self.account_main, units, None, None, None, None)
            )

            if account_sub is not None:
                txn.postings.append(
                    bc_data.Posting(account_sub, - units, None, None, None, None)
                )

            entries.append(txn)
        return entries

    def account_sniffer(self, narration):
        """
        通过正则寻找对应的账户
        假如没有找到对应的账户会增加 ! 标记
        :param narration
        :return: account
        """
        for r_str in self.account_sub.keys():
            if re.search(r_str, narration):
                return self.account_sub[r_str]
        # TODO log record
        self.flag = "!"
        return None

    def narration_beautify(self, narration: str):
        """
        以为内说明条目太丑了, 所以增加了美化环节, 主要是正则匹配后替换
        :param narration:
        :return: 美化后的 narration
        """
        for reg_pat, reg_rep in self.nar_reg.items():
            narration = re.sub(reg_pat, reg_rep, narration).strip()
        return narration
