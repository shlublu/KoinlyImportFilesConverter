#!/bin/python3

'''
Koinly Check: checks the balance change in a Koinly file.

Usage: koinly_check.py path/to/file.csv

Disclaimer: I built this tool for my own use, and I apologize as it looks a bit quick'n'dirty. 
            I am sharing it because if it was useful to me, it might be useful to others. However, it comes with no guarantee of any kind.

Licence: EUPL 1.2 https://joinup.ec.europa.eu/sites/default/files/custom-page/attachment/2020-03/EUPL-1.2%20EN.txt
Author: Vincent Poulain, 2022-2025
'''

import csv
import sys


def usage() -> None:
    print(f'Usage: {sys.argv[0]} path/to/koinly_file.csv', file=sys.stderr)


def csvReader(inputFile: str, delimiter: str) -> csv.reader:
    reader = csv.reader(inputFile, delimiter = delimiter)
    next(reader)

    return reader


def formatAmount(amount: float) -> str:
    strResult = f'{amount:.{20}f}'

    while (strResult[-1] == '0'):
        strResult = strResult[:-1]
  
    if strResult[-1] == '.':
        strResult = strResult[:-1]    
    
    return strResult


def initBalanceChangeForCurrency(balanceChanges: dict, currency: str) -> None:
    if currency and currency not in balanceChanges:
        balanceChanges[currency] = 0


def balanceIncrease(balanceChanges: dict, amount: str, currency: str) -> None:
    if amount:
        balanceChanges[currency] += float(amount)


def balanceDecrease(balanceChanges: dict, amount: str, currency: str) -> None:
    if amount:
        balanceChanges[currency] -= float(amount)


def checkBalanceChanges() -> None:
    if len(sys.argv) != 2:
        return usage()
    
    filePath = sys.argv[1]

    balanceChanges = {}

    try:
        with open(filePath, newline = '') as inputFile:
            reader = csvReader(inputFile, ';')

            for row in reader:
                sentAmount = row[1]
                sentCurrency = row[2]
                receivedAmount = row[3]
                receivedCurrency = row[4]
                feesAmount = row[5]
                feesCurrency = row[6]

                initBalanceChangeForCurrency(balanceChanges, sentCurrency)
                initBalanceChangeForCurrency(balanceChanges, receivedCurrency)
                initBalanceChangeForCurrency(balanceChanges, feesCurrency)

                balanceDecrease(balanceChanges, sentAmount, sentCurrency)
                balanceIncrease(balanceChanges, receivedAmount, receivedCurrency)
                balanceDecrease(balanceChanges, feesAmount, feesCurrency)

        for currency, change in balanceChanges.items():
            print(f'{currency}: {"+" if change > 0 else ""}{formatAmount(change)}')

    except FileNotFoundError as err:
        print(f'Cannot open "{err.filename}": file not found.', file=sys.stderr)


if __name__ == '__main__':
    checkBalanceChanges()
