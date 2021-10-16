from pdfminer.high_level import extract_text
import re
import pandas as pd
from Importer import Col


def read(file) -> pd.DataFrame:
    """
    读取izly的attestation.pdf文件, 然后返回记录日期、金额、事件的dataframe
    :return pandas.dataframe
    """
    filename = file.name
    return read_adp(filename)


def read_adp(filename: str) -> pd.DataFrame:
    # row 未加工的文本
    row = extract_text(filename)
    # 暴力去无用的信息
    start_pos = row.find("€")
    end_pos = row.find("Total")
    text = row[start_pos:end_pos]

    pat_date = re.compile("[0-9]{1,2}/[0-9]{1,2}/20[0-9][0-9]")
    pat_money = re.compile("[-]?[0-9]+,[0-9]{2} €")
    pat_narration = re.compile("Payment|Top-up from Carte bancaire")

    jour = pat_date.findall(text)
    argent = pat_money.findall(text)
    # 类型转化移到了importer中
    # jour = [datetime.datetime.strptime(j, "%m/%d/%Y").date() for j in jour]
    # 格式就直接本地化了
    argent = [i.replace("€", "").replace(",", ".") for i in argent]

    narration = pat_narration.findall(text)
    df = pd.DataFrame({Col.DATE: jour, Col.NARRATION: narration})

    # sort 是因为pdf 中读出来的nar, money 顺序有问题
    df = df.sort_values(by=[Col.NARRATION], ascending=False)
    df[Col.MONEY] = argent

    return df


if __name__ == "__main__":
    print(read_adp('test/AccountStatement-2021-09.pdf'))
