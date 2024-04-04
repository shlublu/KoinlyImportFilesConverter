#!/bin/python

'''
Koinly Converter: converts history files from various CEX (currently just Meria 'Waltio' exports as formerly handled others have ceased operations) to Koinly import files.

Usage: koinly_convert.py meria path/to/file.csv

Disclaimer: I built this tool for my own use, and I apologize as it looks a bit quick'n'dirty. 
            I am sharing it because if it was useful to me, it might be useful to others. However, it comes with no guarantee of any kind.

Default fiat currency notice: the default fiat currency is EUR. Please adjust the variable 'FIAT_BASE_CURRENCY' below to use it with another base currency. 
                              This is very important for Binance Card export files as this corresponds to the card's currency. This is expected to be minor for export files from other CEXs.

Licence: EUPL 1.2 https://joinup.ec.europa.eu/sites/default/files/custom-page/attachment/2020-03/EUPL-1.2%20EN.txt
Author: Vincent Poulain, December 2022
'''

FIAT_BASE_CURRENCY = 'EUR'

CSV_DELIMITER_OUT = ';'
CSV_DELIMITER_IN_BINANCECARD = ';'


class OutputLine:
    def __init__(
        self, 
        txDate, sentAmount, sentCurrency, receivedAmount, receivedCurrency, *, 
        feeAmount = None, feeCurrency = None, netWorthAmount = None, netWorthCurrency = None, label = None, description = None, txHash = None
        ) -> None:
        self.txDate = txDate
        self.sentAmount = sentAmount
        self.sentCurrency = sentCurrency
        self.receivedAmount = receivedAmount
        self.receivedCurrency = receivedCurrency
        self.feeAmount = feeAmount
        self.feeCurrency = feeCurrency
        self.netWorthAmount = netWorthAmount
        self.networthCurrency = netWorthCurrency
        self.label = label
        self.description = description
        self.txHash = txHash


    def toList(self):
        return [
            self.txDate, 
            self.sentAmount, self.sentCurrency, 
            self.receivedAmount, self.receivedCurrency,
            self.feeAmount, self.feeCurrency,
            self.netWorthAmount, self.networthCurrency,
            self.label,
            self.description,
            self.txHash
        ]


    @staticmethod
    def headers():
        return OutputLine(
            txDate = 'Date', 
            sentAmount = 'Sent Amount', sentCurrency = 'Sent Currency', 
            receivedAmount = 'Received Amount', receivedCurrency = 'Received Currency', 
            feeAmount = 'Fee Amount', feeCurrency = 'Fee Currency', 
            netWorthAmount = 'Net Worth Amount', netWorthCurrency = 'Net Worth Currency',
            label = 'Label', 
            description = 'Description', 
            txHash = 'TxHash'
        )


def doConvert():
    import csv
    import os
    import sys

    MODE_MERIA = 'meria'

    if len(sys.argv) != 3:
        print(
            f'Usage: {sys.argv[0]} {MODE_MERIA} path/to/file.csv', 
            file = sys.stderr
        )

    else:
        filePath = sys.argv[2]

        try:
            with open(filePath, newline = '') as inputFile:
                mode = sys.argv[1]
                lines = None

                if mode == MODE_MERIA:
                    lines = convertMeria(inputFile)
                else:
                    print(f'Unknown mode: {mode}. Try "{sys.argv[0]} help" for help.', file = sys.stderr)

        except FileNotFoundError:
            print(f'Cannot open "{filePath}": file not found.', file = sys.stderr)

        splittedPath = os.path.split(filePath)

        with open(os.path.join(splittedPath[0], f'koinly_{splittedPath[1]}'), mode = 'w', newline = '') as outputFile:
            writer = csv.writer(outputFile, delimiter = CSV_DELIMITER_OUT, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(OutputLine.headers().toList())
            for row in lines:
                writer.writerow(row.toList())


def csvReader(inputFile, delimiter):
    import csv

    reader = csv.reader(inputFile, delimiter = delimiter)
    next(reader)

    return reader


def convertMeria(inputFile):
    import sys

    def unhandledTxInfoForTxTypeError(txType, txInfo):
        print(f'Unhandled txInfo for txType {txType}: {txInfo}.', file = sys.stderr)

    normalizeLunaTicker = lambda ticker : ticker if ticker != 'LUNA' else f'{ticker}2'

    reader = csvReader(inputFile, ';')
    lines = []

    for row in reader:
        txHash = row[0] if row[0] != 'n/a' else None
        txType = row[1]
        sourceAmount = row[2]
        sourceCurrency = row[3]
        destinationAmount = row[4]
        destinationCurrency = row[5]
        address = row[6]
        memo = row[7]
        destinationType = row[8]
        feeMultiplier = float(row[9]) / 100.0
        txInfo = row[10]
        txDate = row[11]

        sentAmount = None
        sentCurrency = None
        receivedAmount = None
        receivedCurrency = None
        feeAmount = None
        feeCurrency = None
        label = None
        description = None

        if txType == 'credit':
            if txInfo in ('airdrop', 'deposit', 'order', 'reward', 'unstaking', 'resale'):
                receivedAmount = destinationAmount
                receivedCurrency = destinationCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(receivedAmount))
                    feeCurrency = receivedCurrency

                label = (
                    txInfo if txInfo in ('airdrop', 'reward') else 
                        'unstake' if txInfo in ('unstaking', 'resale') else 
                            'liquidity in' if receivedCurrency == FIAT_BASE_CURRENCY else 
                                None
                )

            elif txInfo in ('claim'):
                pass

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        elif txType == 'debit':
            if txInfo in ('masternode', 'order', 'reinvestment', 'staking'):
                sentAmount = sourceAmount
                sentCurrency = sourceCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(sentAmount))
                    feeCurrency = sentCurrency

                label = (
                    'stake' if txInfo in ('masternode', 'reinvestment', 'staking') else 
                        'cost' if txInfo in ('order') else 
                            None
                )             

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        elif txType == 'exchange':
            if txInfo == '':
                sentAmount = sourceAmount
                sentCurrency = sourceCurrency

                receivedAmount = destinationAmount
                receivedCurrency = destinationCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(sentAmount))
                    feeCurrency = sentCurrency

                label = 'swap'

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        elif txType == 'withdraw':
            if txInfo == '':
                sentAmount = sourceAmount
                sentCurrency = sourceCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(sentAmount))
                    feeCurrency = sentCurrency

                description = f'{destinationType} {address} {memo}'
                label = None

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        else:
            print(f'Unhandled txType: {txType}.', file = sys.stderr)

        lines.append(
            OutputLine(
                txDate = txDate,
                sentAmount = sentAmount, sentCurrency = normalizeLunaTicker(sentCurrency),
                receivedAmount = receivedAmount, receivedCurrency = normalizeLunaTicker(receivedCurrency),
                feeAmount = feeAmount, feeCurrency = normalizeLunaTicker(feeCurrency),
                label = label,
                description = description,
                txHash = txHash
            )
        )

    return lines


if __name__ == '__main__':
    doConvert()

