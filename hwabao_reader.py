import re
import pandas as pd

from stock_importer import Col

from datetime import datetime as dt
from io import StringIO

# 无用的委托类型..
# 指定是开户的, 配号是申购, 托管对记账无影响
drop_list = ["指定", "配号", "中签通知", "托管转出", "托管转入"]
# 同上
drop_col = ["成交时间", "成交编号", "股东代码"]

COL_MAP = {
    "成交日期": Col.DATE,
    "证券代码": Col.ID,
    "证券名称": Col.STOCK,
    "成交价格": Col.PRICE,
    "成交数量": Col.NUMBER,
    "发生金额": Col.AMOUNT_POS,
    "成交金额": Col.AMOUNT_PRE,
    "佣金": Col.COMMISSION,
    "印花税": Col.STAMP,
    "过户费": Col.TRANS,
    "其他费": Col.OTHER,
    "说明": Col.NARRATION
}


def read(file) -> pd.DataFrame:
    csv_data = file.contents()
    return read_adp(csv_data)



def read_adp(file_data):
    start_pos = file_data.find("\n\n")
    raw = file_data[start_pos + 2:]
    # 防止结尾过多空格
    raw = re.sub("\s+\n", " \n ", raw)
    # 成交时间存在空值栏, 导致后面读取会蹿列 所以替换掉,
    raw = re.sub("\s{20}", "  None  ", raw)
    df = pd.read_csv(StringIO(raw), sep='\s+')

    df["成交日期"] = df["成交日期"].apply(lambda x: dt.strptime(str(x), "%Y%m%d").date())
    df.drop(columns=drop_col, inplace=True)

    # 可转债

    # 可转债申购中签
    ind = df[df["委托类别"] == "中签扣款"].index
    df.loc[ind, "成交数量"] = df.loc[ind, "成交金额"] / df.loc[ind, "成交价格"]
    df.loc[ind, "委托类别"] = "申购"
    # 代码变更 申购的代码和交易时的代码不同，
    for i in ind:
        # 后面两个字基本是转债， 可能有特例导致无法识别
        name = df.at[i, "证券名称"][:2]
        for j, row in df[df['委托类别'] == "托管转入"].iterrows():
            if row["证券名称"].find(name) > -1:
                df.at[i, "证券代码"] = row["证券代码"]
                break

    # 可转债出售
    # 可转债卖出莫名其妙是一份, 所以就修改一遍数量
    ind = df[df["委托类别"] == "卖出"].index
    df.loc[ind, "成交数量"] = round(df.loc[ind, "成交金额"] / df.loc[ind, "成交价格"])

    # R-001 逆回购特殊处理
    ind = df[df["证券名称"] == "Ｒ-001"].index
    df.loc[ind, "成交价格"] = 100

    # 扔掉无用的委托, 华宝系统独特..
    mask = df['委托类别'].apply(lambda x: x not in drop_list)
    df = df[mask]

    # TODO 基金申购金额会有少量不对, 因为对应基金的净值是四位数小数... 但是华宝给的价格是三位数
    # 个人的方法是 直接把价格内的空格去了..

    # 交易取名
    df["说明"] = df["委托类别"] + " " + df["成交数量"].apply(str) + " 份 " + df["证券代码"].apply(str) + "@" + df["证券名称"]
    df.rename(columns=COL_MAP, inplace=True)

    return df


if __name__ == "__main__":
    with open("test/20211025 交割单查询.txt", "r", encoding="gb2312") as f:
        data = f.read()
    print(read_adp(data))
